# Format: https://oracc.museum.upenn.edu/osl/ASLOSLFileFormat/index.html

from pathlib import Path

from bs4 import BeautifulSoup
from tqdm import tqdm

URL = 'https://oracc.museum.upenn.edu/osl/downloads/sl.xml' # The JSON has syntax errors, so going for XML instead - somehow it's actually a smaller file, so I'm guessing the JSON has a really awful schema (or is just corrupt in some way)
FILE = Path.cwd() / 'data' / 'sl.xml'

# The parts of the format we care about are:
#	<sl:signlist>
#		<sl:listdef name="HZL"> // Sign lists specified here
#			<sl:info>1-100 200-250 96A 196(1)</sl:info> // Numbers can be preceded by 0x to mark hex, this is only done for Unicode codepoints afaict
#			<sl:lit>Author, Title (Year)</sl:lit>
#		</sl:listdef>
#		<sl:letter> // Alphabetical indexing
#			<sl:sign n="NAME"> // Sign name in caps
#				<sl:name>
#					<g:w form="NAME">
#						// Then either:
#						<g:s>NAME</g:s> // S = sign
#						// Or:
#						<g:c> // C = composition
#							<g:s>SIGN IN NAME</g:s>
#							<g:o g:type="OPERATOR">
#							<g:s>SIGN IN NAME</g:s>
#						<g:c>
#					</g:w>
#				</sl:name>
#				<sl:list n="HZL1234" /> // No space between prefix and number
#				<sl:ucun hex="U+12345">𒀉</sl:ucun> // For single glyphs, OR
#				<sl:ucun hex="x12345.x12346">𒄩𒀀</sl:ucun> // For glyph sequences
#				<sl:v n="VALUE"> // Value name in lowercase
#					<sl:name>
#						<g:w form="VALUE">
#							<g:v>VALUE</g:v>
#						</g:w>
#					</sl:name>
#				</sl:v>
#			</sl:sign>
#		</sl:letter>
#	</sl:signlist>

def download_data():
	import requests
	r = requests.get(URL, verify=False) # The SSL certificate is broken, bypass it
	r.encoding = 'UTF-8' # Avoid error
	with FILE.open('w') as f: # You can also just wget it if this causes problems or if you don't have the requests library
		f.write(r.text)

class Sign:
	def __init__(self, name, unicode=None, values=(), composition=None):
		self.name = name
		self.unicode = unicode # List of Unicode codepoints, as ints, or None
		self.values = list(values) # List of possible readings, as strings
		self.composition = composition # Either a string representing the composition of this sign, or None if it can't be decomposed further

class SignList:
	def __init__(self, prefix, desired_signs=()):
		self.prefix = prefix
		self.desired_signs = set(desired_signs) # Which signs do we hope to find in the database? Stored as strings, not ints
		self.signs = {} # Sign list ID : Sign
	
	def process_number_list(self, rawnums):
		pass # TODO
	
	def handle_xml(self, xml):
		if not isinstance(xml, BeautifulSoup):
			with open(xml, 'r') as f:
				xml = BeautifulSoup(f.read(), 'xml')
		root = xml.find('sl:signlist')
		if not root: raise ValueError('Expected <sl:signlist> tag as root')
		
		ldef = root.find('sl:listdef', attrs={'name':self.prefix})
		if not ldef:
			names = [l.name for l in root.findall('sl:listdef')]
			raise ValueError(f'Could not find <sl:listdef> with name "{self.prefix}". Found {len(names)} others: {" ".join(names)}.')
		
		lname = ldef.find('sl:lit')
		if not lname: raise ValueError('Expected <sl:lit> tag inside <sl:listdef>')
		self.formal_name = str(lname.string)
		
		linfo = ldef.find('sl:info')
		if not linfo: raise ValueError('Expected <sl:info> tag inside <sl:listdef>')
		rawnums = str(linfo.string)
		self.process_number_list(rawnums)
		
		for letter in tqdm(root.find_all('sl:letter', recursive=False)):
			sign_count = 1
			for sign in tqdm(letter.find_all('sl:sign', recursive=False)):
				try:
					self.process_sign(sign)
				except:
					print(f'Error in letter {letter["name"]}, entry {sign_count}, name {sign["n"]}')
					raise
	
	def parse_composition_data(self, tag):
		results = []
		for child in tag.children:
			if child.prefix == 'g' and child.name == 's': results.append(str(child.string)) # Signs have their names stored in the tag's string
			elif child.prefix == 'g' and child.name == 'r': results.append(str(child.string)) # Same for numbers of repetitions
			elif child.prefix == 'g' and child.name == 'm': results.append(str(child.string)) # Same for modifiers
			elif child.prefix == 'g' and child.name == 'o': results.append(child['g:type']) # Operators have their names stored in the tag's attributes
			elif child.prefix == 'g' and child.name == 'n': results.append(self.parse_composition_data(child)) # Non-parenthesized grouping
			elif child.prefix == 'g' and child.name == 'g': results.append('(' + self.parse_composition_data(child) + ')') # Groups are, well...groups
			else: raise ValueError(child)
		return ' '.join(results)
	
	def process_sign(self, tag):
		# First, figure out if this is a sign in our list or not
		for l in tag.find_all('sl:list', recursive=False):
			listname = l['n'] # "HZL1234"
			if listname.startswith(self.prefix): # It's the one we want!
				ident = listname.removeprefix(self.prefix)
				break
		else: # Nothing found, this sign is not in our list
			return
		
		sign = Sign(tag['n'])
		
		w = tag.find('sl:name').find('g:w') # This is where composition data will be stored, if there is any
		if c := w.find('g:c'): # Group composition
			sign.composition = self.parse_composition_data(c)
		
		if u := tag.find('sl:ucun'): # Unicode data - TODO do any signs lack this?
			code = u['hex']
			if code.startswith('U+'): # Single codepoint
				sign.unicode = [int(code.removeprefix('U+'), 16)]
			elif '.' in code:
				codes = code.split('.')
				codes = [c if c != 'X' else '0000' for c in codes] # Change X's to zeroes TODO temporary
				sign.unicode = [int(c.removeprefix('x'), 16) for c in codes]
			else:
				raise ValueError(code)
		
		for v in tag.find_all('sl:v', recursive=False): # Sign value
			sign.values.append(v['n'].lower())
		
		self.signs[ident] = sign

if __name__ == '__main__':
	if not FILE.exists():
		print('Downloading data...')
		download_data()
		print('Data downloaded')
	
	input()
	s = SignList('HZL')
	s.handle_xml(FILE)
	print(f'Found {len(s.signs)} signs!')

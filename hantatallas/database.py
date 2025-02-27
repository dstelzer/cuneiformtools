from collections import defaultdict
from urllib.parse import urlencode
import html
import re

try:
	from parser import parse
	from layout import Spacer, Ruling, Fill
	from elements import ModeFlag
except ImportError:
	from .parser import parse
	from .layout import Spacer, Ruling, Fill
	from .elements import ModeFlag

norm_modes = { # Which normalization modes are currently supported
	'normal' : frozenset({}),
	'gottstein' : frozenset({ModeFlag.GOTTSTEIN}),
}

def dict_list_factory(): return defaultdict(list)

class DatabaseForm: # A sign form, with its tags - this could be a namedtuple but I want to give it methods
	def __init__(self, code, tags=()):
		self.code = code
		self.tags = frozenset(tags)
	
	def matches(self, query):
		return tuple(q in self.tags for q in query) # Return a tuple showing which of the tags our form matches, to sort by
	
	@classmethod
	def from_line(cls, line):
		components = line.strip().split()
		if len(components) == 1: return cls(components[0]) # No tags
		return cls(components[0], components[1:]) # Tags!

class DatabaseEntry:
	def __init__(self):
		self.ident = None # internal ID, must be unique
		self.langs = defaultdict(list) # lang -> [reading]
		self.forms = [] # [code]
		self.notes = defaultdict(dict_list_factory) # lang -> name -> [meaning]
		self.names = set() # names to reference this sign by
		self.ident_sort = None # form of `ident` to sort by
	
	def finalize(self):
		self.functional = {}
		try:
			for mk, mv in norm_modes.items(): # Make a separate entry for each normalization mode
				self.functional[mk] = [parse(f.code).functional_form(mv) for f in self.forms]
		except ValueError:
			print(f'(Error while handling {self.ident} in {mk} mode)')
			raise
		self.names.add('#'+str(self.ident)) # Fallback name in case nothing else is provided
		if m := re.match(r'(\d+)(\D*)', self.ident): # Expect an int followed by zero or more letters
			self.ident_sort = (int(m[1]), m[2]) # So sort first by the int, then by the letters
		else:
			self.ident_sort = -1, self.ident # If it doesn't follow this pattern, put it first so it stands out (and we can fix it)
	
	def sort_ident(self):
		return self.ident_sort
	def sort_complex(self):
		if not self.functional['normal']: raise ValueError('No forms found', self.name)
		return self.functional['normal'][0].complexity()
	def sort_usage(self):
		# `not` because we want signs which *do* have an entry for a specific language to come first in the sorting
		# So this is equivalent to 0 if there is an entry, 1 if there's not, and 0 < 1
		return (
			not self.langs['HIT'],
			self.langs['HIT'][0] if self.langs['HIT'] else '',
			not self.langs['HURR'],
			self.langs['HURR'][0] if self.langs['HURR'] else '',
			not self.langs['AKK'],
			self.langs['AKK'][0] if self.langs['AKK'] else '',
			not self.langs['DET'],
			self.langs['DET'][0] if self.langs['DET'] else '',
			not self.langs['SUM'],
			self.langs['SUM'][0] if self.langs['SUM'] else '',
		)
	
	def find_matches(self, part=None, regex=None, tags=(), mode='normal'):
		tags = tuple(tags)
		if regex is not None:
			if not any(re.search(regex, name) for name in self.names):
				return # We didn't match the regex
		for i, (pres, func) in enumerate(zip(self.forms, self.functional[mode])):
	#		if not any(pres.matches(tags)): # Filter out forms based on the tags
	#			continue
	# TODO: should tags be considered in this method at all?
			if part is None:
				ident = f'{self.ident}/{i+1}' if i else str(self.ident)
				yield ident, pres, ()
			elif part in func:
				ident = f'{self.ident}/{i+1}' if i else str(self.ident)
				match = func.highlight_containment(part)
				yield ident, pres, match

class Database:
	def __init__(self):
		self.name = None
		self.data = []
		self.sorted = defaultdict(list)
		self.name_lookup = {}
		self.cleanup = {}
		self.expansions = {}
		self.attested_rows = set() # Which rows (like HIT, AKK, etc) are found in the database?
	
	def load_cleanup(self, fn):
		with open(fn, 'r') as f:
			lines = f.read().split('\n')
			for line in lines:
				if not line: continue
				source, target = line.split('\t')
				self.cleanup[source] = target
		return self
	
	def load_expansions(self, fn):
		with open(fn, 'r') as f:
			lines = f.read().split('\n')
			for line in lines:
				if not line: continue
				source, target = line.split('\t')
				expand = list(target.split('.'))
				self.expansions[source] = expand
		return self
	
	def load_data(self, fn):
		with open(fn, 'r') as f:
			lines = f.read().split('\n')
			current_language = None
			current_form = None
			entry = None
			for line in lines:
				tabs = len(line) - len(line.lstrip())
				line = line.strip()
				if not line: continue
				if tabs == 0: # Sign ID
					if entry:
						entry.finalize()
						self.data.append(entry)
						self.attested_rows |= set(entry.langs.keys())
					entry = DatabaseEntry()
					entry.ident = line
	#				print('Processing', line)
				elif tabs == 1: # Language category
					current_language = line
				elif tabs == 2: # Form
					if current_language == 'FORM':
						entry.forms.append(DatabaseForm.from_line(line))
					elif current_language == 'NAME':
						names = line.upper().split()
						for name in names:
							entry.names.add(name)
							if name in self.name_lookup: raise ValueError(f'Name {name} for sign {entry.ident} already taken by sign {self.name_lookup[name].ident}')
							self.name_lookup[name] = entry
					else:
						entry.langs[current_language].append(line)
					current_form = line
				elif tabs == 3: # Elaboration of some sort
					entry.notes[current_language][current_form].append(line)
			if entry:
				entry.finalize()
				self.data.append(entry)
				self.attested_rows |= set(entry.langs.keys())
		return self
	
	def clean_name(self, name):
		name = name.upper()
		for source, target in self.cleanup.items():
			name = name.replace(source, target)
		return name
	
	def prepare_sorting(self):
		self.sorted['ident'] = sorted(self.data, key=DatabaseEntry.sort_ident)
		self.sorted['complex'] = sorted(self.data, key=DatabaseEntry.sort_complex)
		self.sorted['usage'] = sorted(self.data, key=DatabaseEntry.sort_usage)
	
	def lookup(self, part, regex, tags=(), mode='normal'):
		func = part.functional_form()
		for entry in self.data:
			yield from entry.find_matches(func, regex, tags, mode)
	
	def name_to_glyph(self, name, tags=()):
		name = self.clean_name(name)
		if name in self.expansions: # An expansion name shouldn't be passed to this function
			exp = '.'.join(self.expansions[name])
			raise ValueError(f'Sign {name} is shorthand for {exp}')
		
		if '/' in name: # We have name/variant instead of just name
			try:
				name, variant = name.split('/')
			except ValueError as e:
				raise ValueError(f'Malformed sign name {name}: expected either name or name/variant')
			name = name.strip()
			variant = variant.strip()
			
			try: # Is the variant a number?
				variant = int(variant)
			except ValueError: # Nope!
				pass
		else: # It's just a name, set variant to None
			name = name.strip()
			variant = None
		
		if name not in self.name_lookup: raise ValueError(f'Unknown sign name {name}')
		
		entry = self.name_lookup[name]
		
		if isinstance(variant, int): # Do we have a variant number?
			# If so, we ignore the tags, and take that numbered variant from the dictionary
			if len(entry.forms) < variant: raise ValueError(f'Sign {name} has only {len(entry.forms)} variant(s); cannot produce {variant}')
			code = entry.forms[variant-1].code # -1 because the first one is 1 not 0, following the HZL's practice
		else: # No variant number specified, so we're looking for the form that maximizes our tags
			if variant is not None: # Do we have a variant that's not a number? If so, we add it to the front of our tags list
				tags = (variant,) + tags
			# Then we take the form that maximally matches our tags
			# The `matches` method returns a tuple of booleans showing which tags matched in which order, so we maximize that tuple
			form = max((f for f in entry.forms), key=lambda f: f.matches(tags))
			code = form.code
		
		return parse(code)
	
	def parse_transcription(self, trans, tags=()): # Go from a textual transcription to a list of rows of signs and spacers
		# Special codes: `n newline, `r ruling, `w word sep, `f hfill, `F damaged hfill
		# (Not used here: `s sign sep in raw sequence parser)
		results = []
		trans = trans.replace('\r', '') # Carriage returns are the bane of text processing
		trans = trans.replace('\n`r\n', '`r') # Standardize newlines on either side of a ruling: first remove them if they're present
		trans = trans.replace('`n`r`n', '`r') # Whether written literally or with escapes
		# (We're assuming nobody writes \n`r`n or `n`r\n)
		trans = trans.replace('`r', '\n`r\n') # Then impose them uniformly everywhere
		trans = trans.replace('`n', '\n') # For circumstances where newlines aren't possible, we've defined a control-character-less alternative. Here, we turn that into a normal newline.
		# TODO - Also recognize `r with newlines on only one side
		for i, line in enumerate(trans.split('\n')):
			if line.strip() == '`r': # Check for a special case: rulings
				results.append(Ruling())
				continue
			
			row = []
			line = line.strip() # Remove lingering space on either end
	#		line = re.sub(r'\s*(`[wfF])\s*', r'.\1.', line) # Remove any whitespace surrounding separators and fillers
			line = re.sub(r'\s+', '.`w.', line) # Replace whitespace with `w (word separator)
			line = line.replace('-', '.') # Standardize separators; dot and dash are treated equivalently here
			line = line.replace('^', '.') # Similarly ^ for determiners
			for j, unit in enumerate(line.split('.')):
				try:
					if not unit: continue
					if unit == '`w': # Special code for a spacer
						row.append(Spacer())
					elif unit == '`f': # Fill
						row.append(Fill())
					elif unit == '`F': # Damaged fill
						row.append(Fill(damaged=True))
					elif unit.startswith('%'): # Recursive code rather than sign name
						row.append(parse(unit[1:]))
					else:
						unit = self.clean_name(unit)
						if unit in self.expansions:
							for subunit in self.expansions[unit]:
								if subunit not in self.name_lookup: raise ValueError(f'Internal problem in expansion of {unit}: could not find subunit {subunit}. Please report this!') # This should never happen, ideally - it means we've defined a compound logogram that refers to a simple logogram that doesn't exist
								row.append(self.name_to_glyph(subunit, tags))
						else:
							row.append(self.name_to_glyph(unit, tags))
				except ValueError as e:
					print(f'Parse error in line {i+1}, sign {j+1}')
					if e.args: print('\n'.join(e.args))
					raise
			results.append(row)
		return results
	
	ROWS = { # Order the rows should appear in, depending what rows are in the database
		'IDENT' : 'Ident',
		'TAGS' : 'Tags',
		'FORM' : 'Sign',
		'HIT' : 'In Hittite words',
		'HURR' : 'In foreign words',
		'AKK' : 'In Akkadian words',
		'DET' : 'Determinative',
		'SUM' : 'Sumerogram',
		'LIG' : 'Compounds',
		'CODE' : 'Code',
		'NOTE' : 'Notes',
		'COMP' : 'Composition',
	}
	
	@staticmethod
	def prettify_plaintext(text, colspan=1, always_expand=False, start_checked=False): # All plaintext fields from the database (i.e. all fields except CODE, IDENT, and FORM) are run through this before being printed, letting us do a little bit of formatting on them
		def make_link(m):
			num = m.group(1)
			query = urlencode({'regex' : fr'^\#{num}$'})
			searchurl = f'/search?{query}'
			return f'<a href="{searchurl}">#{num}</a>'
		
		text = re.sub(r'<([^>]+)>', r'<em>\1</em>', text)
		text = re.sub(r'#([0-9A-Z]+)', make_link, text)
		width = max(len(s) for s in text.split('\n')) # Length of the longest line
		height = len(text.split('\n'))
		text = text.replace('\n', '<br />')
		
		if (width > 25 * colspan or height > 4) and not always_expand:
			if '<br />' in text: extra = '<br />'
			else: extra = ''
			if start_checked: check = ' checked'
			else: check = ''
			text = f'<label class="showlong">Show long text? <input type="checkbox"{check} /></label><span class="hidden">{extra}{text}</span>'
		
		return text
	
	# Present results as an HTML table - this is kind of a mess and deserves refactoring
	def lookup_as_table(self, part=None, regex=None, tags=(), mode='normal', sort='ident', start_checked=False, rendersign_path='/rendersign', signinfo_path='/search?regex=^%23{}%24'): # rendersign_path allows this to be run locally instead of on a server, for testing - point it to the actual web URL of the renderer instead of a local path
		
		used_rows = {k:v for k,v in self.ROWS.items() if k in self.attested_rows | {'IDENT', 'FORM', 'TAGS', 'CODE'}} # Which table rows do we actually need? ROWS specifies the order of them
		# We always include these four, because they're generated from the other data in the entry instead of stored in the .langs data, which means they won't be in attested_rows
		rows = {k: [f'<tr id="{k.lower()}"><th scope="row">{v}</th>'] for k,v in used_rows.items()} # Each key gets a list of cells forming its row; we start with the th cell, which will appear at the left as a legend and hover over the rest
		
		func = part.functional_form(norm_modes[mode]) if part else None
		matches = 0 # How many distinct signs (not forms) have matched so far? This is reported at the end of the search
		temp = [] # We need to know the number of entries before formatting them, so we store our intermediate results here before formatting
		
		for entry in self.sorted[sort]: # Use the self.sorted array to iterate over them in the correct order
			matching_forms = list(entry.find_matches(func, regex, mode))
			if matching_forms: # One or more of these forms matched!
				matches += 1
				temp.append((entry, matching_forms))
		
		# We now know how many matches we have, so we can format them appropriately
		for entry, matching_forms in temp:
			colspan = len(matching_forms) # For the TAGS, FORM, and CODE columns, we have separate cells for each form; for all the rest, we have a single cell covering all of them, which has colspan="{colspan}"
			for _, pres, match in matching_forms: # So we handle those three first
				raw = {'code':pres.code}
				if match: raw['highlight'] = ','.join(str(s) for s in match)
				query = urlencode(raw)
				rows['FORM'].append(f'<td><img src="{rendersign_path}?{query}" height="100px" /></td>') # Form row: a rendered image of the form
				rows['CODE'].append(f'<td><tt>{pres.code}</tt></td>') # Code row: the code that leads to that form
				rows['TAGS'].append(f'<td>{", ".join(pres.tags)}</td>') # Tags row: form-specific tags used to select this form over others
				# (Any sign-specific rather than form-specific information goes in NOTE instead)
			
			# The fourth universal row is IDENT, which is the internal identifier of this entry, generally the sign list index number
			rows['IDENT'].append(f'<td colspan="{colspan}">#{entry.ident}</td>')
			
			# All the rest vary depending on the database file; we just include whichever ones are available
			for lang in self.attested_rows:
				rs = []
				for reading in entry.langs[lang]: # Since they're defaultdicts in the entry, we can query whichever ones we want, it'll just return [] if it doesn't exist (which means this for-loop will immediately exit)
					notes = entry.notes[lang][reading] # Do we have any notes on this specific reading?
					if notes:
						if any(',' in n or '(' in n for n in notes):
							sep = '; '
						else:
							sep = ', '
						notes = sep.join(notes)
						rs.append(f'{reading} “{notes}”')
					else:
						rs.append(reading)
				if any(',' in r or '(' in r or '“' in r for r in rs):
					sep = '\n' # Will become <br /> in prettify_plaintext
				else:
					sep = ', '
				rs = sep.join(rs)
				rs = self.prettify_plaintext(rs, colspan, matches==1, start_checked)
				if len(rs) > 25 and colspan < 2: # Add a bit of padding in this particular case, because this is when the cramping is worst
					extra = ' class="minwidth"'
				else:
					extra= ''
				rows[lang].append(f'<td colspan="{colspan}"{extra}>{rs}</td>')
		
		# Finally, close all the row tags
		for row in rows: rows[row].append('</tr>')
		
		# Wrap it in a table tag, and return it along with the count of matches
		return matches, '<table>' + ''.join(''.join(row) for row in rows.values()) + '</table>'

def preview_database(fn):
	import webbrowser
	db = Database()
	db.load_data(fn)
	db.prepare_sorting()
	print('Loaded', fn)
	while True:
		part = input('Part: ') or None
		regex = input('Regex: ') or None
		tags = input('Tags: ') or None
		if tags: tags = tags.split()
		matches, table = db.lookup_as_table(part, regex, tags, rendersign_path='https://dstelzer.pythonanywhere.com/rendersign') # Use the remote server address instead so this can be run locally
		print(matches, 'match'+('es' if matches != 1 else ''))
		with open('tmp.html', 'w') as f:
			# The basic styling that's needed for the table to be readable
			f.write('''<html><head><style>
			table, th, td {
				border: 1px solid black;
				border-collapse: collapse;
			}
			th {
				background-color: #AAAAAA;
				position: sticky;
				z-index: 100;
				left: 0;
			}
			.minwidth {
				min-width: 10em;
			}
			.hidden {
				display: block;
				height: 0;
				width: 0;
				overflow: hidden;
			}
			label.showlong:has(input:checked) ~ .hidden {
				display: inline;
			}
			label.showlong {
				font-size: smaller;
				font-style: italic;
				color: #888888;
			}
			</style></head>\n<body>\n''')
			f.write(table) # Beyond that, nothing but the table, no frills
			f.write('\n</body></html>')
		webbrowser.open('tmp.html')

def eval_database():
	from elements import Superpose, Stroke
	from collections import Counter
	def is_improper(root): # A tree is *improper* if there are two strokes of the same type with a superposition as their last common ancestor
		for elem in root.traverse():
			if isinstance(elem, Superpose): # Iterate over superpositions
				strokesets = []
				for child in elem.contents: # For each child, make a set of all the stroke types appearing in that child
					ss = {type(s) for s in child.traverse_strokes()}
					strokesets.append(ss)
				# Now if any type appears in more than one of those sets, we have an improper tree
				counts = Counter()
				for ss in strokesets:
					counts.update(ss)
				# I.e. if any of these counts is > 1
				for k,v in counts.items():
					if 'Void' in k.__name__: continue
					if v > 1:
						return f'{k.__name__}, {str(elem)}'
		return None
	
	from elements import Modifier
	def is_anomalous(root):
		for elem in root.traverse_strokes():
			if Modifier.INVERT in elem.mods or Modifier.TRIPLE in elem.mods:
				return True
		return False
	
	db = Database()
	db.load_data('data/hzl.dat')
	db.load_expansions('data/replacements.dat')
	db.prepare_sorting()
	print('Total', len(db.data))
	print('Not Hittite', sum(1 for e in db.data if not e.langs['HIT']))
	print('Sumerian and not Hittite', sum(1 for e in db.data if e.langs['SUM'] and not e.langs['HIT']))
	print('Forms', sum(len(e.forms) for e in db.data))
	
	print('Improper:')
	y = 0
	for e in db.data:
		x = 0
		for i, f in enumerate(e.forms):
			repeat = is_improper(parse(f.code))
			if repeat is not None:
				x += 1
				print(f'\t{e.ident}/{i+1}: {repeat}')
		if x:
			print(f'\t\t{x}/{i+1}')
			y += 1
	print(f'\tTotal: {y}')
	
	print('Anomalous:')
	for e in db.data:
		for i, f in enumerate(e.forms):
			if is_anomalous(parse(f.code)):
				print(f'\t{e.ident}/{i+1}')

def use_database():
	db = Database()
	db.load_data('data/hzl.dat')
	db.load_expansions('data/replacements.dat')
	db.prepare_sorting()
	while True:
		for name, code, match in db.lookup(parse(input('Code: ')), re.compile(input('Regex: ')), input('Mode: ')):
			print(name, code, match)

if __name__ == '__main__':
	preview_database('data/hzl.dat')

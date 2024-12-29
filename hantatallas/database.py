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
	
	# Present results as an HTML table - this is kind of a mess and deserves refactoring
	def lookup_as_table(self, part=None, regex=None, tags=(), mode='normal', sort='ident', rendersign_path='/rendersign'):
		
		func = part.functional_form(norm_modes[mode]) if part else None
		rows = [
			['<tr id="ident"><th scope="row">Ident</th>'],
			['<tr id="tags"><th scope="row">Tags</th>'],
			['<tr id="form"><th scope="row">Sign</th>'],
			['<tr id="hit"><th scope="row">In Hittite</th>'],
			['<tr id="hurr"><th scope="row">In foreign words</th>'],
			['<tr id="akk"><th scope="row">In Akkadian</th>'],
			['<tr id="sum"><th scope="row">Sumerogram</th>'],
			['<tr id="det"><th scope="row">Determinative</th>'],
			['<tr id="code"><th scope="row">Code</th>'],
			['<tr id="note"><th scope="row">Notes</th>'],
		]
		
		IDENT, TAGS, FORM, HIT, HURR, AKK, SUM, DET, CODE, NOTE = range(10)
		
		matches = 0
		
		for entry in self.sorted[sort]:
			matching_forms = list(entry.find_matches(func, regex, mode))
			if matching_forms:
				matches += 1
				colspan = len(matching_forms)
				for _, pres, match in matching_forms:
					raw = {'code':pres.code}
					if match: raw['highlight'] = ','.join(str(s) for s in match)
					query = urlencode(raw)
					rows[FORM].append(f'<td><img src="{rendersign_path}?{query}" height="100px" /></td>')
					rows[CODE].append(f'<td><tt>{pres.code}</tt></td>')
					rows[TAGS].append(f'<td>{", ".join(pres.tags)}</td>')
				
				ident = entry.ident
				rows[IDENT].append(f'<td colspan="{colspan}">{ident}</td>')
				
				hittite = ', '.join(entry.langs['HIT'])
				rows[HIT].append(f'<td colspan="{colspan}">{hittite}</td>')
				
				foreign = ', '.join(entry.langs['HURR'])
				rows[HURR].append(f'<td colspan="{colspan}">{foreign}</td>')
				
				akkadian = ', '.join(entry.langs['AKK'])
				rows[AKK].append(f'<td colspan="{colspan}">{akkadian}</td>')
				
				note = '; '.join(entry.langs['COMP'] + entry.langs['NOTE'])
				rows[NOTE].append(f'<td colspan="{colspan}">{note}</td>')
				
				def meanings1(sg): return ', '.join(entry.notes['SUM'][sg])
				sumerian = ', '.join(f'{sg} "{meanings1(sg)}"' for sg in entry.langs['SUM'])
				rows[SUM].append(f'<td colspan="{colspan}">{sumerian}</td>')
				
				def meanings2(sg): return ', '.join(entry.notes['DET'][sg])
				determinative = ', '.join(f'{sg} "{meanings2(sg)}"' for sg in entry.langs['DET'])
				rows[DET].append(f'<td colspan="{colspan}">{determinative}</td>')
		for row in rows: row.append('</tr>')
		
		return matches, '<table>' + ''.join(''.join(row) for row in rows) + '</table>'

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
		matches, table = db.lookup_as_table(part, regex, tags, rendersign_path='https://dstelzer.pythonanywhere.com/rendersign')
		print(matches, 'match'+('es' if matches != 1 else ''))
		with open('tmp.html', 'w') as f:
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
			</style></head>\n<body>\n''')
			f.write(table)
			f.write('\n</body></html>')
		webbrowser.open('tmp.html')

if __name__ == '__main__':
	
	preview_database('data/huehnergard.dat')
	
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
	
	while True:
		for name, code, match in db.lookup(parse(input('Code: ')), re.compile(input('Regex: ')), input('Mode: ')):
			print(name, code, match)

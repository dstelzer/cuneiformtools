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

class DatabaseEntry:
	def __init__(self):
		self.ident = None # internal ID, must be unique
		self.langs = defaultdict(list) # lang -> [reading]
		self.forms = [] # [Canvas]
		self.notes = defaultdict(dict_list_factory) # lang -> name -> [meaning]
		self.names = set() # names to reference this sign by
	
	def finalize(self):
		self.functional = {}
		try:
			for mk, mv in norm_modes.items(): # Make a separate entry for each normalization mode
				self.functional[mk] = [parse(f).functional_form(mv) for f in self.forms]
		except ValueError:
			print(f'(Error while handling {self.ident} in {mk} mode)')
			raise
		self.names.add('HZL'+str(self.ident)) # Fallback name in case nothing else is provided
	
	def sort_hzl(self):
		return self.ident.zfill(3)
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
	
	def find_matches(self, part=None, regex=None, mode='normal'):
		if regex is not None:
			if not any(re.search(regex, name) for name in self.names):
				return # We didn't match the regex
		for i, (pres, func) in enumerate(zip(self.forms, self.functional[mode])):
			if part is None:
				ident = f'{self.ident}/{i}' if i else str(self.ident)
				yield ident, pres, ()
			elif part in func:
				ident = f'{self.ident}/{i}' if i else str(self.ident)
				match = func.highlight_containment(part)
				yield ident, pres, match

class Database:
	def __init__(self):
		self.data = []
		self.sorted = defaultdict(list)
		self.name_lookup = {}
		self.cleanup = {}
		self.expansions = {}
	
	def load_cleanup(self, fn):
		with open(fn, 'r') as f:
			lines = f.read().split('\n')
			for line in lines:
				source, target = line.split('\t')
				self.cleanup[source] = target
	
	def load_expansions(self, fn):
		with open(fn, 'r') as f:
			lines = f.read().split('\n')
			for line in lines:
				source, target = line.split('\t')
				expand = list(target.split('.'))
				self.expansions[source] = expand
	
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
				elif tabs == 1: # Language
					current_language = line
				elif tabs == 2: # Form
					if current_language == 'FORM':
						entry.forms.append(line)
					elif current_language == 'NAME':
						names = line.upper().split()
						for name in names:
							entry.names.add(name)
							if name in self.name_lookup: raise ValueError(f'Name {name} for sign {entry.ident} already taken by sign {self.name_lookup[name].ident}')
							self.name_lookup[name] = entry
					else:
						entry.langs[current_language].append(line)
					current_form = line
				elif tabs == 3: # Sumerogram definition or elaboration
					entry.notes[current_language][current_form].append(line)
			if entry:
				entry.finalize()
				self.data.append(entry)
	
	def clean_name(self, name):
		name = name.upper()
		for source, target in self.cleanup.items():
			name = name.replace(source, target)
		return name
	
	def prepare_sorting(self):
		self.sorted['hzl'] = sorted(self.data, key=DatabaseEntry.sort_hzl)
		self.sorted['complex'] = sorted(self.data, key=DatabaseEntry.sort_complex)
		self.sorted['usage'] = sorted(self.data, key=DatabaseEntry.sort_usage)
	
	def lookup(self, part, regex, mode='normal'):
		func = part.functional_form()
		for entry in self.data:
			yield from entry.find_matches(func, regex, mode)
	
	def name_to_glyph(self, name):
		name = self.clean_name(name)
		if name in self.expansions:
			exp = '.'.join(self.expansions[name])
			raise ValueError(f'Sign {name} is shorthand for {exp}')
		
		if '/' in name: name, variant = name.split('/')
		else: variant = '1'
		name = name.strip()
		variant = int(variant.strip())
		
		if name not in self.name_lookup: raise ValueError(f'Unknown sign name {name}')
		
		entry = self.name_lookup[name]
		if len(entry.forms) < variant: raise ValueError(f'Sign {name} has only {len(entry.forms)} variant(s); cannot produce {variant}')
		
		return parse(entry.forms[variant-1])
	
	def parse_transcription(self, trans): # Go from a textual transcription to a list of rows of signs and spacers
		# Special codes: `n newline, `r ruling, `w word sep, `f hfill
		# (Not used here: `s sign sep in raw sequence parser)
		results = []
		trans = trans.replace('\r', '') # Carriage returns are the bane of text processing
		trans = trans.replace('\n`r\n', '`r') # Standardize newlines on either side of a ruling: first remove them if they're present
		trans = trans.replace('`n`r`n', '`r') # Whether written literally or with escapes
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
								row.append(self.name_lookup[subunit])
						else:
							row.append(self.name_to_glyph(unit))
				except ValueError as e:
					print(f'Parse error in line {i+1}, sign {j+1}')
					if e.args: print('\n'.join(e.args))
					raise
			results.append(row)
		return results
	
	# Present results as an HTML table - this is kind of a mess and deserves refactoring
	def lookup_as_table(self, part=None, regex=None, mode='normal', sort='hzl'):
		
		func = part.functional_form(norm_modes[mode]) if part else None
		rows = [
			['<tr id="hzl"><th scope="row">HZL Number</th>'],
			['<tr id="comp"><th scope="row">Composition</th>'],
			['<tr id="form"><th scope="row">Sign</th>'],
			['<tr id="hit"><th scope="row">In Hittite</th>'],
			['<tr id="hurr"><th scope="row">In foreign words</th>'],
			['<tr id="akk"><th scope="row">In Akkadian</th>'],
			['<tr id="sum"><th scope="row">Sumerogram</th>'],
			['<tr id="det"><th scope="row">Determinative</th>'],
			['<tr id="code"><th scope="row">Code</th>'],
		]
		
		matches = 0
		
		for entry in self.sorted[sort]:
			matching_forms = list(entry.find_matches(func, regex, mode))
			if matching_forms:
				matches += 1
				colspan = len(matching_forms)
				for ident, pres, match in matching_forms:
					raw = {'code':pres}
					if match: raw['highlight'] = ','.join(str(s) for s in match)
					query = urlencode(raw)
					rows[2].append(f'<td><img src="/rendersign?{query}" height="100px" /></td>')
					rows[8].append(f'<td><tt>{pres}</tt></td>')
				
				hzl = entry.ident
				rows[0].append(f'<td colspan="{colspan}">{hzl}</td>')
				
				comp = ', '.join(entry.langs['COMP'])
				rows[1].append(f'<td colspan="{colspan}">{comp}</td>')
				
				hittite = ', '.join(entry.langs['HIT'])
				rows[3].append(f'<td colspan="{colspan}">{hittite}</td>')
				
				foreign = ', '.join(entry.langs['HURR'])
				rows[4].append(f'<td colspan="{colspan}">{foreign}</td>')
				
				akkadian = ', '.join(entry.langs['AKK'])
				rows[5].append(f'<td colspan="{colspan}">{akkadian}</td>')
				
				def meanings1(sg): return ', '.join(entry.notes['SUM'][sg])
				sumerian = ', '.join(f'{sg} "{meanings1(sg)}"' for sg in entry.langs['SUM'])
				rows[6].append(f'<td colspan="{colspan}">{sumerian}</td>')
				
				def meanings2(sg): return ', '.join(entry.notes['DET'][sg])
				determinative = ', '.join(f'{sg} "{meanings2(sg)}"' for sg in entry.langs['DET'])
				rows[7].append(f'<td colspan="{colspan}">{determinative}</td>')
		for row in rows: row.append('</td></tr>')
		
		return matches, '<table>' + ''.join(''.join(row) for row in rows) + '</table>'

if __name__ == '__main__':
	db = Database()
	db.load_data('data/hzl.dat')
	db.prepare_sorting()
	print('Not Hittite', sum(1 for e in db.data if not e.langs['HIT']))
	print('Sumerian and not Hittite', sum(1 for e in db.data if e.langs['SUM'] and not e.langs['HIT']))
	while True:
		for name, code, match in db.lookup(parse(input('Code: ')), re.compile(input('Regex: ')), input('Mode: ')):
			print(name, code, match)

from collections import defaultdict
from urllib.parse import urlencode
import html

try:
	from parser import parse
except ImportError:
	from .parser import parse

class DatabaseEntry:
	def __init__(self):
		self.name = None
		self.langs = defaultdict(list)
		self.forms = []
		self.sumerogram = defaultdict(list) # ech, kind of hacky TODO
	
	def finalize(self):
		try:
			self.functional = [parse(f).functional_form() for f in self.forms]
		except ValueError:
			print(f'(Error while handling {self.name})')
			raise
	
	def sort_hzl(self):
		return self.name.zfill(3)
	def sort_complex(self):
		if not self.functional: raise ValueError('No forms found', self.name)
		return self.functional[0].complexity()
	def sort_usage(self): # `not` because we want signs which *do* have an entry for a specific language to come first in the sorting
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
	
	def find_matches(self, part):
		for i, (pres, func) in enumerate(zip(self.forms, self.functional)):
			if part in func:
				ident = f'{self.name}/{i}' if i else str(self.name)
				match = func.highlight_containment(part)
				yield ident, pres, match
	
	def yield_all(self):
		for i, pres in enumerate(self.forms):
			ident = f'{self.name}/{i}' if i else str(self.name)
			yield ident, pres, ()

class Database:
	def __init__(self):
		self.data = []
		self.sorted = defaultdict(list)
	
	def load_file(self, fn):
		with open(fn, 'r') as f:
			lines = f.read().split('\n')
			current_language = None
			current_form = None
			entry = None
			for line in lines:
				tabs = len(line) - len(line.lstrip())
				line = line.strip()
				if not line: continue
				if tabs == 0: # Sign name
					if entry:
						entry.finalize()
						self.data.append(entry)
					entry = DatabaseEntry()
					entry.name = line
				elif tabs == 1: # Language
					current_language = line
				elif tabs == 2: # Form
					if current_language == 'FORM': entry.forms.append(line)
					else: entry.langs[current_language].append(line)
					current_form = line
				elif tabs == 3: # Sumerogram definition
					entry.sumerogram[current_form].append(line)
			if entry:
				entry.finalize()
				self.data.append(entry)
	
	def prepare_sorting(self):
		self.sorted['hzl'] = sorted(self.data, key=DatabaseEntry.sort_hzl)
		self.sorted['complex'] = sorted(self.data, key=DatabaseEntry.sort_complex)
		self.sorted['usage'] = sorted(self.data, key=DatabaseEntry.sort_usage)
	
	def lookup(self, part):
		func = part.functional_form()
		for entry in self.data:
			yield from entry.find_matches(func)
	
	def yield_all(self): # TODO: probably not needed now due to wildcards
		for entry in self.data:
			yield from entry.yield_all()
	
	# Present results as an HTML table
	def lookup_as_table(self, part, sort='hzl'):
		func = part.functional_form()
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
			matching_forms = list(entry.find_matches(func))
			if matching_forms:
				matches += 1
				colspan = len(matching_forms)
				for ident, pres, match in matching_forms:
					raw = {'code':pres}
					if match: raw['highlight'] = ','.join(str(s) for s in match)
					query = urlencode(raw)
					rows[2].append(f'<td><img src="/rendersign?{query}" height="100px" /></td>')
					rows[8].append(f'<td><tt>{pres}</tt></td>')
				
				hzl = entry.name
				rows[0].append(f'<td colspan="{colspan}">{hzl}</td>')
				
				comp = ', '.join(entry.langs['COMP'])
				rows[1].append(f'<td colspan="{colspan}">{comp}</td>')
				
				hittite = ', '.join(entry.langs['HIT'])
				rows[3].append(f'<td colspan="{colspan}">{hittite}</td>')
				
				foreign = ', '.join(entry.langs['HURR'])
				rows[4].append(f'<td colspan="{colspan}">{foreign}</td>')
				
				akkadian = ', '.join(entry.langs['AKK'])
				rows[5].append(f'<td colspan="{colspan}">{akkadian}</td>')
				
				def meanings(sg): return ', '.join(entry.sumerogram[sg])
				sumerian = ', '.join(f'{sg} "{meanings(sg)}"' for sg in entry.langs['SUM'])
				rows[6].append(f'<td colspan="{colspan}">{sumerian}</td>')
				
				determinative = ', '.join(f'{sg} "{meanings(sg)}"' for sg in entry.langs['DET'])
				rows[7].append(f'<td colspan="{colspan}">{determinative}</td>')
		for row in rows: row.append('</td></tr>')
		
		return matches, '<table>' + ''.join(''.join(row) for row in rows) + '</table>'

if __name__ == '__main__':
	db = Database()
	db.load_file('data/hzl.dat')
	db.prepare_sorting()
	while True:
		for name, code, match in db.lookup(parse(input())):
			print(name, code, match)

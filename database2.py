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
	
	def lookup(self, part):
		func = part.functional_form()
		for entry in self.data:
			yield from entry.find_matches(func)
	
	def yield_all(self): # TODO: probably not needed now due to wildcards
		for entry in self.data:
			yield from entry.yield_all()
	
	# Present results as an HTML table
	def lookup_as_table(self, part):
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
		]
		
		found = False
		
		for entry in self.data:
			matching_forms = list(entry.find_matches(func))
			if matching_forms:
				found = True
				colspan = len(matching_forms)
				for ident, pres, match in matching_forms:
					raw = {'text':pres, 'type':'publish'}
					if match: raw['highlight'] = ','.join(str(s) for s in match)
					query = urlencode(raw)
					rows[2].append(f'<td><img src="/hantatallas_process?{query}" height="100px" /></td>')
				
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
				
				determinative = ', '.join(entry.langs['DET'])
				rows[7].append(f'<td colspan="{colspan}">{determinative}</td>')
		for row in rows: row.append('</td></tr>')
		
		if not found: return '<p>No results found</p>'
		
		return '<table>' + ''.join(''.join(row) for row in rows) + '</table>'

if __name__ == '__main__':
	db = Database()
	db.load_file('data/work.txt')
	while True:
		for name, code, match in db.lookup(parse(input())):
			print(name, code, match)

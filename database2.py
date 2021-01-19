from collections import defaultdict

from parser import parse

class DatabaseEntry:
	def __init__(self):
		self.name = None
		self.langs = defaultdict(list)
		self.forms = []

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
				elif tabs == 3: # Sumerogram definition
					# TODO IMPLEMENT THIS
					pass
			if entry:
				entry.finalize()
				self.data.append(entry)
	
	def lookup(self, part):
		func = part.functional_form()
		for entry in self.data:
			yield from entry.find_matches(func)
	
	def yield_all(self):
		for entry in self.data:
			yield from entry.yield_all()

if __name__ == '__main__':
	db = Database()
	db.load_file('data/work.txt')
	while True:
		for name, code, match in db.lookup(parse(input())):
			print(name, code, match)

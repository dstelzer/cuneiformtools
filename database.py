import csv

from .parser import parse

class DatabaseEntry:
	def __init__(self, name, code, notes=''):
		self.name = name
		self.code = code
		self.notes = notes
		self.presentation = parse(code)
		self.functional = self.presentation.functional_form()

class Database:
	def __init__(self):
		self.data = {}
	
	def load_file(self, fn):
		with open(fn, 'r', newline='') as f:
			read = csv.reader(f, delimiter='\t')
			for i, row in enumerate(read):
				if not row: continue
				name = row[0]
				try:
					self.data[name] = DatabaseEntry(*row)
				except ValueError as e:
					print(f'(Error occurred on line {i} of file {fn}, parsing {name})')
					raise
	
	def lookup(self, part):
		func = part.functional_form()
		for entry in self.data.values():
			if func in entry.functional:
				yield entry

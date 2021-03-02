

from render import *
from parser import parse, parse_sequence
from database import Database

def test_rendering():
	while True:
		try:
			construct = parse(input())
			print(construct)
			print(construct.functional_form())
			TwoSidedRenderer.render(construct).show()
		#	TwoSidedRenderer.render(construct, ('1')).show()
		#	TwoSidedRenderer.render(construct.functional_form()).show()
		except ValueError: pass

def test_group_rendering():
	while True:
		try:
			seq = parse_sequence(input())
		#	full = input()
		#	rows = []
		#	for line in full.split('`n'):
		#		row = []
		#		for sign in line.split('`s'):
		#			row.append(parse(sign))
		#		rows.append(row)
			TwoSidedRenderer.render_sequence(seq, justify='r').show()
		except ValueError: pass

def test_comparisons():
	while True:
		outer = parse(input('Outer: '))
		outf = outer.functional_form()
		inner = parse(input('Inner: '))
		inf = inner.functional_form()
		if inf in outf:
			match = outf.highlight_containment(inf)
	#		print(match)
			TwoSidedRenderer.render(outer, match).show()
		else:
			print('No match')

def test_database():
	db = Database()
	for fn in ['data/cv.tsv', 'data/vc.tsv']:
		db.load_file(fn)
	while True:
		cmd, code = input().strip().split(' ')
		if cmd.lower() == 's':
			part = parse(code)
			print(', '.join(e.name for e in db.lookup(part)))
		elif cmd.lower() == 'p':
			tree = db.data[code].presentation
			TwoSidedRenderer.render(tree).show()

if __name__ == '__main__':
	test_group_rendering()

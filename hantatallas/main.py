

from render import *
from parser import parse, parse_sequence
from layout import Layout
from database import Database

def test_rendering():
	while True:
		try:
			construct = parse(input(), friendly=True)
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
			TwoSidedRenderer.render_sequence(seq, justify='c').show()
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

def test_layout():
	db = Database()
	db.load_cleanup('data/cleanup.dat')
	db.load_expansions('data/replacements.dat')
	db.load_data('data/hzl.dat')
	db.prepare_sorting()
	while True:
		desc = input()
		Layout(TriangleRenderer, justify='s').render(db.parse_transcription(desc), fill=True).show()

def test_uga():
	db = Database()
	db.load_data('data/uga.dat')
	db.prepare_sorting()
	while True:
		desc = input()
		Layout(TwoSidedRenderer, justify='l', spacing=0.67).render(db.parse_transcription(desc), fill=True).show()

if __name__ == '__main__':
	test_rendering()

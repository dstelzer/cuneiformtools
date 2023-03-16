

from render import *
from parser import parse, parse_sequence
from layout import Layout
from database import Database

def test_rendering():
	while True:
		try:
			construct = parse(input() or 'S([0\'"v!]h2)', friendly=True)
			print(construct)
			print(construct.functional_form())
			print(construct.forest())
			TwoSidedRenderer.render(construct, margin=32).show()
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
		print(outf)
		inner = parse(input('Inner: '))
		inf = inner.functional_form()
		print(inf)
		if inf in outf:
			match = outf.highlight_containment(inf)
	#		print(match)
			print('Match')
			TwoSidedRenderer.render(outer, match).show()
		else:
			print('No match')
		print()

def test_layout():
	db = Database()
	db.load_cleanup('data/cleanup.dat')
	db.load_expansions('data/replacements.dat')
	db.load_data('data/hzl.dat')
	db.prepare_sorting()
	while True:
		desc = input()
		if not desc: desc = 'nu NINDA-an e-ez-za-at-te-ni `n wa-a-tar-ma e-ku-ut-te-ni `r nu NINDA-an `F'
		Layout(TriangleRenderer, justify='s').render(db.parse_transcription(desc), fill=True).show()

def test_uga():
	db = Database()
	db.load_data('data/uga.dat')
	db.prepare_sorting()
	while True:
		desc = input()
		Layout(TwoSidedRenderer, justify='l', spacing=0.67).render(db.parse_transcription(desc), fill=True).show()

if __name__ == '__main__':
	test_layout()

# Test case for stack containment: Outer: [v{h[{cc}{cc}]h}v] Inner: {h[cc][cc]h}
# Should match, currently doesn't



from render import *
from render3d import *
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
			InkRenderer.render(construct, margin=32).show()
		#	TwoSidedRenderer.render(construct, ('1')).show()
		#	TwoSidedRenderer.render(construct.functional_form()).show()
		except ValueError: pass

def test_group_rendering():
	while True:
		try:
			seq = parse_sequence(input())
			SharpInkRenderer.render_sequence(seq, justify='c').show()
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
		if not desc: desc = 'nu NINDA-an e-ez-za-at-te-ni/3 `n wa-a-tar-ma e-ku-ut-te-ni/3 `r nu NINDA-an `F'
		Layout(SharpInkRenderer, justify='s', size=256, margin=0.25).render(db.parse_transcription(desc), strokewidth=0.05).show()
	#	Layout(ScadRenderer, justify='s', size=10, margin=0.25).render(db.parse_transcription(desc), fill=True, thickness=5, shape='seal').show()
	#	Layout(ScadRenderer, justify='s', size=10, margin=0.25).render(db.parse_transcription(desc), fill=True, thickness=5, shape='tablet').show()

def test_uga():
	db = Database()
	db.load_data('data/uga.dat')
	db.prepare_sorting()
	while True:
		desc = input()
		Layout(TwoSidedRenderer, justify='l', spacing=0.67).render(db.parse_transcription(desc), fill=True).show()

def regression_testing():
	with open('regression.in', 'r') as f1:
		with open('regression.out', 'w') as f2:
			for line in f1:
				print('.', end='', flush=True)
				construct = parse(line.strip())
				func = construct.functional_form()
				f2.write(str(func)+'\n')
	print('Done')

if __name__ == '__main__':
	test_layout()

# Test case for stack containment: Outer: [v{h[{cc}{cc}]h}v] Inner: {h[cc][cc]h}
# Should match, currently doesn't

# Crash comes from {h[0{cc}{hh}{hh}0]h} - FIXED

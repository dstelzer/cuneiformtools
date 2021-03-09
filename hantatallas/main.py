

from render import *
from parser import parse, parse_sequence

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

if __name__ == '__main__':
	test_group_rendering()

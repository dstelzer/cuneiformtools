

from render import *
from parser import parse

if __name__ == '__main__':
	while True:
		try:
			construct = parse(input())
			print(construct)
			print(construct.functional_form())
			TwoSidedRenderer.render(construct).show()
		#	TwoSidedRenderer.render(construct.functional_form()).show()
		except ValueError: pass

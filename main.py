

from render import *
from parser import parse

if __name__ == '__main__':
	while True:
		try:
			construct = parse(input())
			print(construct)
			TwoSidedRenderer.render(construct).show()
		except ValueError: pass

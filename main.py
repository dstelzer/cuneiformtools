

from render import TwoSidedRenderer
from parser import parse

if __name__ == '__main__':
	while True:
		try:
			construct = parse(input())
		except ValueError: pass
		print(construct)
		TwoSidedRenderer.render(construct).show()

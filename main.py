

from render import TwoSidedRenderer
from parser import parse

if __name__ == '__main__':
	rend = TwoSidedRenderer(256, 256)
	while True:
		construct = parse(input())
		print(construct)
		construct.propagate_dimensions()
		rend.blank()
		construct.draw(rend)
		rend.show()

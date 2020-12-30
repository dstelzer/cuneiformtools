

from render import TwoSidedRenderer
from parser import parse

if __name__ == '__main__':
	while True:
		construct = parse(input())
		print(construct)
		TwoSidedRenderer.render(construct).show()

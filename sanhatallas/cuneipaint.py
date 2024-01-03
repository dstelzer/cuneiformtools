from sys import exit, path
from pathlib import Path
import json

from geometry import XY
from sketch import Line, Divider, HookLine, LineGroup

path.append(str(Path(__file__).parents[1]))
from hantatallas.hack import render, lookup

classes = {
	'STROKE' : Line,
	'HOOK' : HookLine,
	'DIVIDE' : Divider,
}

def convert_object(obj):
	cls = classes[obj['type']]
	start = XY(float(obj['x1']), float(obj['y1']))
	end = XY(float(obj['x2']), float(obj['y2']))
	
	return cls(start, end)

def convert_list(lst):
	return LineGroup([convert_object(o) for o in lst])

def convert_json(s):
	return convert_list(json.loads(s))

def handle(s):
	linegroup = convert_json(s)
	converted = str(linegroup.parse())
	render(converted)

if __name__ == '__main__':
	while True:
		handle(input('>'))

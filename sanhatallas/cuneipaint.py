from sys import exit, path
from pathlib import Path
import json

try:
	from geometry import XY
	from strokeparse import Line, DoubleLine, TripleLine, Divider, HookLine, LineGroup
except ImportError:
	from .geometry import XY
	from .strokeparse import Line, DoubleLine, TripleLine, Divider, HookLine, LineGroup

if __name__ == '__main__':
	path.append(str(Path(__file__).parents[1]))
	from hantatallas.hack import render, lookup

classes = {
	'STROKE' : Line,
	'DOUBLE' : DoubleLine,
	'TRIPLE' : TripleLine, # Never actually produced yet, but future-proofing
	'HOOK' : HookLine,
	'DIVIDE' : Divider,
}

TOLERANCE = 10

def convert_object(obj):
	cls = classes[obj['type']]
	start = XY(obj['head']['x'], obj['head']['y'])
	end = XY(obj['tail']['x'], obj['tail']['y'])
	
	return cls(start, end, tolerance=TOLERANCE)

def convert_list(lst):
	return LineGroup([convert_object(o) for o in lst])

def convert_json(s):
	return convert_list(json.loads(s))

def handle(s):
	linegroup = convert_json(s)
	converted = str(linegroup.parse())
	render(converted)

def paint_process(s, tolerance=None):
	global TOLERANCE # TODO: can we do this without a global?
	if tolerance is not None: TOLERANCE = tolerance
	
	try:
		linegroup = convert_json(s)
		converted = str(linegroup.parse())
		return json.dumps({'success':True, 'result':converted})
	except ValueError as e:
		err = f'{str(e)} ({type(e).__name__})'
		return json.dumps({'success':False, 'result':err})

if __name__ == '__main__':
	while True:
		handle(input('>'))

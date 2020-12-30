

from elements import *

STARTS = '([{<'
ENDS = ')]}>'
MODS = ''

SHAPES = 'PLSW'
STROKES = 'hHvVuUdDc0'
NUMBERS = '123456789'

IGNORE = ', \t\n\v'

class ParseFrame:
	def __init__(self, start=0, initial=False):
		self.start = start
		self.end = start
		self.initial = initial
		self.contents = []
	
	def finish(self):
		if self.initial: raise ValueError('Unmatched closer', self.contents[-1])
		
		a = self.contents[0]
		z = self.contents[-1]
		if a not in STARTS or z not in ENDS: raise ValueError('Bad delimiters', a, z)
		if STARTS.index(a) != ENDS.index(z): raise ValueError('Delimiters don\'t match', a, z)
		
		if a == '[':
			type = HStack
		elif a == '{':
			type = VStack
		elif a == '(':
			type = Superpose
		elif a == '<':
			type = Nudge
		
		if len(self.contents) < 3: raise ValueError('Empty container')
		
		return type(self.contents[1:-1])

def make_stroke(char):
	if   char == 'h': return Horizontal(False)
	elif char == 'H': return Horizontal(True)
	elif char == 'v': return Vertical(False)
	elif char == 'V': return Vertical(True)
	elif char == 'd': return DownDiag(False)
	elif char == 'D': return DownDiag(True)
	elif char == 'u': return UpDiag(False)
	elif char == 'U': return UpDiag(True)
	elif char == 'c': return Winkelhaken()
	elif char == '0': return Void()

def report_error(error, string, start, end):
	print('Parse error:', error)
	print(string)
	print(' '*start + '~'*(end-start) + '^')

def internal_parse(string, container_stack=None): # The actual parsing, which can throw ValueErrors if something is wrong
	shape = 'S' # Default if not specified
	if container_stack is None: container_stack = [ParseFrame(initial=True)]
	
	for i, char in enumerate(string):
		container_stack[-1].end = i
		
		if i == 0 and char in SHAPES: # First char may indicate shape
			shape = CanvasShape(char)
			continue
		
		elif char in IGNORE: continue
		
		elif char in STARTS:
			new_frame = ParseFrame(i)
			container_stack.append(new_frame)
			container_stack[-1].contents.append(char)
		
		elif char in ENDS:
			if container_stack[-1].initial: raise ValueError('Unmatched closer')
			frame = container_stack.pop(-1)
			frame.contents.append(char)
			output = frame.finish()
			container_stack[-1].contents.append(output)
		
		elif char in STROKES:
			stroke = make_stroke(char)
			container_stack[-1].contents.append(stroke)
		
		elif char in NUMBERS:
			num = Number(char)
			container_stack[-1].contents.append(num)
		
		elif char in MODS:
			container_stack[-1].contents[-1].add_modifier(char)
		
		else:
			raise ValueError('Unrecognized character', char)
	
	if len(container_stack) > 1:
		raise ValueError('Unmatched opener', container_stack[-1].contents[0])
	if not container_stack[0].contents:
		raise ValueError('Empty canvas')
	if len(container_stack[0].contents) > 1:
		raise ValueError('Unconnected elements', container_stack[0].contents)
	
	return Canvas(shape, container_stack[0].contents[0])

def parse(string): # A wrapper around internal_parse for error reporting
	container_stack = [ParseFrame(initial=True)] # We keep this in the outer function to be able to access it during error reporting
	try:
		out = internal_parse(string, container_stack)
	except ValueError as e:
		msg = e.args[0]
		start = container_stack[-1].start
		end = container_stack[-1].end
		report_error(msg, string, start, end)
		raise
	return out

if __name__ == '__main__':
	while True:
		s = input()
		try:
			g = parse(s)
			print(g)
		except ValueError: pass

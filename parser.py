

try:
	from elements import *
except ImportError:
	from .elements import *

STARTS = '([{'
ENDS = ')]}'
MODS = set(m.value for m in Modifier)
ADJS = {
	'T':Tenu,
	'E':Expand,
	'M':Margin,
}

SHAPES = set(s.value for s in CanvasShape)
STROKES = {
	'h':Horizontal,
	'v':Vertical,
	'u':UpDiag,
	'd':DownDiag,
	'c':Winkelhaken,
	'0':Void,
	'*':Wildcard,
}

IGNORE = ', \t\n\v'

class ParseFrame:
	def __init__(self, start=0, initial=False):
		self.start = start
		self.end = start
		self.initial = initial
		self.contents = []
	
	def add(self, element):
		self.contents.append(element)
	
	def finish(self, friendly=False, unfinished=False):
		if self.initial: raise ValueError('Unmatched closer', self.contents[-1])
		
		if unfinished:
			a = self.contents[0]
			if a not in STARTS: raise ValueError('Bad delimiter', a)
			z = ENDS[STARTS.index(a)]
			self.contents.append(z)
		
		a = self.contents[0]
		z = self.contents[-1]
		
		if a not in STARTS or z not in ENDS: raise ValueError('Bad delimiters', a, z)
		if STARTS.index(a) != ENDS.index(z): raise ValueError('Delimiters don\'t match', a, z)
		
		if a == '[':
			newtype = HStack
		elif a == '{':
			newtype = VStack
		elif a == '(':
			newtype = Superpose
		
		if len(self.contents) < 3:
			if friendly: self.contents.insert(1, Wildcard('-1'))
			else: raise ValueError('Empty container')
		
		return newtype(self.contents[1:-1])

def report_error(error, string, start, end):
	print('Parse error:', error)
	print(string)
	print(' '*start + '~'*(end-start) + '^')

def internal_parse(string, container_stack=None, friendly=False): # The actual parsing, which can throw ValueErrors if something is wrong
	shape = 'S' # Default if not specified
	looking_for_adjustment = False
	if container_stack is None: container_stack = [ParseFrame(initial=True)]
	stroke_counter = 0
	
	for i, char in enumerate(string):
		container_stack[-1].end = i
		
		if i == 0 and char in SHAPES: # First char may indicate shape
			shape = CanvasShape(char)
			continue
		
		elif char in IGNORE: continue
		
		elif char in STARTS:
			new_frame = ParseFrame(i)
			container_stack.append(new_frame)
			container_stack[-1].add(char)
	#		if char == '<': looking_for_adjustment = True
		
		elif char in ADJS and looking_for_adjustment:
			adj = ADJS[char]
			container_stack[-1].add(adj)
	#		looking_for_adjustment = False
		
		elif char in ENDS:
			if container_stack[-1].initial: raise ValueError('Unmatched closer')
			frame = container_stack.pop(-1)
			frame.add(char)
			output = frame.finish(friendly)
			container_stack[-1].add(output)
		
		elif char in STROKES:
			stroke = STROKES[char](str(stroke_counter)) # The parentheses are because we want to construct one, not just get the type
			container_stack[-1].add(stroke)
			stroke_counter += 1
		
		elif char in MODS:
			container_stack[-1].contents[-1].add_modifier(char)
		
		elif char in ADJS:
			adj = ADJS[char] # Get the class of the adjustment we want
			container_stack[-1].contents[-1] = adj(container_stack[-1].contents[-1]) # And replace the most recent element with an instance of that class containing that adjustment
		
		else:
			raise ValueError('Unrecognized character', char)
	
	if len(container_stack) > 1:
		if friendly:
			while len(container_stack) > 1:
				frame = container_stack.pop(-1)
				output = frame.finish(friendly, unfinished=True)
				container_stack[-1].add(output)
		else: raise ValueError('Unmatched opener', container_stack[-1].contents[0])
	if not container_stack[0].contents:
		if friendly: container_stack[0].contents.append(Void('-1'))
		else: raise ValueError('Empty canvas')
	if len(container_stack[0].contents) > 1:
		raise ValueError('Unconnected elements', container_stack[0].contents)
	
	return Canvas(shape, container_stack[0].contents[0])

def parse(string, friendly=False): # A wrapper around internal_parse for error reporting
	container_stack = [ParseFrame(initial=True)] # We keep this in the outer function to be able to access it during error reporting
	try:
		out = internal_parse(string, container_stack, friendly)
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

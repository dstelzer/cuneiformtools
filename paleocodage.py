

class Composition:
	def __init__(self, children=()):
		self.children = list(children)
	def __str__(self):
		if len(self.children) == 1: return str(self.children[0])
		else: return self.left + ','.join(str(c) for c in self.children) + self.right

class HStack(Composition):
	left = '['
	right = ']'
class VStack(Composition):
	left = '{'
	right = '}'
class Superpose(Composition):
	left = '('
	right = ')'

class Stroke:
	def __init__(self, mods=()):
		self.mods = list(mods)
	def __str__(self):
		return self.sigil + ''.join(str(m) for m in self.mods)

class Horiz(Stroke):
	sigil = 'h'
class Vert(Stroke):
	sigil = 'v'
class Down(Stroke):
	sigil = 'd'
class Up(Stroke):
	sigil = 'u'
class Hook(Stroke):
	sigil = 'c'

class Mod:
	def __str__(self):
		return self.sigil

def split_by(data, sep): # Split data into lists by a separator
	current = []
	lists = []
	for c in data:
		if c in sep:
			lists.append(current)
			current = []
		else:
			current.append(c)
	lists.append(current)
	return lists

def replace_ab_ac(data, a, b, c): # Replace sequence ab with ac, leaving the rest unchanged
	out = []
	last = None
	for this in data:
		if last == a and this == b: out.append(c)
		else: out.append(this)
		last = this
	return out

def split_underscore(data):
	lists = split_by(data, '_')
	return HStack([
		split_semicolon(l) for l in lists
	])

def split_semicolon(data):
	lists = split_by(data, ';')
	return VStack([
		enclose_first(l) for l in lists
	])

def enclose_first(data):
	return Superpose([
		split_dash(data)
	])

def split_dash(data):
	d2 = replace_ab_ac(data, 'a', '-', '_')
	lists = split_by(d2, '_')
	return HStack([
		split_colon(l) for l in lists
	])

def split_colon(data):
	d2 = replace_ab_ac(data, 'b', ':', ';')
	lists = split_by(d2, ';')
	return VStack([
		enclose_second(l) for l in lists
	])

def enclose_second(data):
	return Superpose(list(
		filter(None, (
			strokify(c) for c in data
		))
	))

def strokify(char):
	if char == 'a': return Vert()
	elif char == 'b': return Horiz()
	elif char == 'c': return Down()
	elif char == 'd': return Up()
	elif char == 'w': return Hook()
	else: return None # Ignore all others

if __name__ == '__main__':
	while True:
		print(split_underscore(input('> ')))

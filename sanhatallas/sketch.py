from collections import defaultdict, namedtuple
from math import atan2, pi
from enum import Enum, auto

from geometry import XY, intersects

Interval = namedtuple('Interval', 'low high')
TaggedInterval = namedtuple('TaggedInterval', 'low high ref')
AABB = namedtuple('AABB', 'xlow ylow xhigh yhigh')

class Orient(Enum):
	HORIZ = auto()
	VERT = auto()
	DOWNDIAG = auto()
	UPDIAG = auto()
	
	def is_diagonal(self):
		return self == Orient.DOWNDIAG or self == Orient.UPDIAG
	
	@staticmethod
	def from_angle(angle): # Currently does not care about reversal
		threshold = pi/8
		d0 = 0
		d90 = pi/2
		d180 = pi
		d270 = 3*pi/2
		d360 = 2*pi
		if angle < 0: angle += 2*pi
		if angle < d0+threshold: return Orient.HORIZ
		elif d0+threshold <= angle < d90-threshold: return Orient.DOWNDIAG
		elif d90-threshold <= angle < d90+threshold: return Orient.VERT
		elif d90+threshold <= angle < d180-threshold: return Orient.UPDIAG
		elif d180-threshold <= angle < d180+threshold: return Orient.HORIZ
		elif d180+threshold <= angle < d270-threshold: return Orient.DOWNDIAG
		elif d270-threshold <= angle < d270+threshold: return Orient.VERT
		elif d270+threshold <= angle < d360-threshold: return Orient.UPDIAG
		else: return Orient.HORIZ

class Line:
	def __init__(self, head, tail):
		self.head = head
		self.tail = tail
		
		xlow = min(head.x, tail.x)
		xhigh = max(head.x, tail.x)
		ylow = min(head.y, tail.y)
		yhigh = max(head.y, tail.y)
		self.aabb = AABB(xlow, ylow, xhigh, yhigh)
		
		self.angle = atan2(tail.y-head.y, tail.x-head.x)
		self.orient = Orient.from_angle(self.angle)
	
	def to_interval(self, axis):
		if axis == Orient.HORIZ: return TaggedInterval(self.aabb.xlow, self.aabb.xhigh, self)
		elif axis == Orient.VERT: return TaggedInterval(self.aabb.ylow, self.aabb.yhigh, self)
		else: raise ValueError(axis)
	
	def __mod__(self, other): # Overloading the modulo operator to mean line intersection
		if not isinstance(other, Line): raise ValueError(other)
		# See notes above for how this works
		return intersects(self.head, self.tail, other.head, other.tail)

class LineGroup:
	def __init__(self, children):
		self.children = list(children)
	
	def strokify(self): # If we have only one child, return it as a stroke
		child = self.children[0]
		if child.orient == Orient.HORIZ: return Horizontal()
		elif child.orient == Orient.VERT: return Vertical()
		elif child.orient == Orient.UPDIAG: return Upward()
		elif child.orient == Orient.DOWNDIAG: return Downward()
		else: raise ValueError(child.orient)
	
	def try_to_divide(self, axis):
		# First, convert every line to an interval on the appropriate axis
		intervals = [c.to_interval(axis) for c in self.children]
		# Sort by starting point
		intervals.sort(key = lambda i: i.low)
		
		# Run through the intervals and see which ones overlap
		current = None # Current interval under consideration
		results = [] # What we return: list of lists of lines
		for i in intervals:
			if current is not None and current.high >= i.low: # This one overlaps the previous interval: combine them
				current = Interval(current.low, max(current.high, i.high)) # We know the previous one had a lower low, because of the sorting
				# But we don't know if this one had a higher high: it's possible for one interval to be entirely contained within another
				results[-1].append(i.ref)
			else: # No overlap (or no stack): this is a new component
				current = i
				results.append([i.ref])
		
		return results
	
	# Divide the children into maximal subsets such that any two elements of a subset do not intersect
	# TODO: Is this truly maximal? That is, will it always give the smallest possible number of subsets?
	def partition(self):
		bins = []
		
		for child in self.children: # For each child…
			for bin in bins: # …run through the bins…
				for other in bin: # …and for each bin, see if it conflicts with any element in that bin
					if child % other: break
				else: # Didn't intersect with anything? Put it in this bin!
					bin.append(child)
					break
			else: # Ran out of bins? Make a new one!
				bins.append([child])
		
		return bins
	
	def parse(self):
		# First, check for a single stroke (or zero) as our base case
		if len(self.children) == 1:
			return self.strokify()
		if len(self.children) == 0:
			raise ValueError()
		
		# First, check for tenu
		pass # TODO
		
		# Second, check for horizontal stack
		hdiv = self.try_to_divide(Orient.HORIZ)
		# Third, check for vertical stack
		vdiv = self.try_to_divide(Orient.VERT)
		
		if len(hdiv) > 1 and len(vdiv) > 1: # We could divide either way: need a heuristic to decide!
			pass # TODO
		
		if len(hdiv) > 1: # We can divide horizontally!
			print(hdiv)
			return HStack( [LineGroup(g).parse() for g in hdiv] )
		
		if len(vdiv) > 1: # We can divide vertically!
			return VStack( [LineGroup(g).parse() for g in vdiv] )
		
		# Fourth, divide into non-intersecting components
		cdiv = self.partition()
		if len(cdiv) > 1: # We can form useful partitions!
			return Superpose( [LineGroup(g).parse() for g in cdiv] )
		
		# That last one should be guaranteed to succeed. If it doesn't, then something has gone very wrong.
		raise ValueError('Not able to divide!', self.children)

class Element:
	def __init__(self, raw=None):
		self.process(raw)
	def process(self, raw):
		raise NotImplemented
	def str(self):
		raise NotImplemented
class Composition(Element):
	def process(self, raw):
		if not isinstance(raw, list): raise ValueError('List needed', raw)
		self.children = raw
class Stroke(Element):
	def process(self, raw):
		if raw: raise ValueError('should be nothing', raw)
	def __str__(self): return self.sigil()
class HStack(Composition):
	def __str__(self): return '[' + ','.join(str(c) for c in self.children) + ']'
class VStack(Composition):
	def __str__(self): return '{' + ','.join(str(c) for c in self.children) + '}'
class Superpose(Composition):
	def __str__(self): return '(' + ','.join(str(c) for c in self.children) + ')'
class Horizontal(Stroke):
	def sigil(self): return 'h'
class Vertical(Stroke):
	def sigil(self): return 'v'
class Downward(Stroke):
	def sigil(self): return 'd'
class Upward(Stroke):
	def sigil(self): return 'u'
class Winkelhaken(Stroke):
	def sigil(self): return 'c'

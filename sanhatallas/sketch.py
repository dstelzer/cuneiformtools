from collections import defaultdict, namedtuple
from math import atan2, pi
from enum import Enum, auto
from statistics import mean

try:
	from geometry import XY, intersects, rotate, magnitude, distalong
except ImportError:
	from .geometry import XY, intersects, rotate, magnitude, distalong

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
	def __init__(self, head, tail, tolerance=0):
		# First, we want to adjust its length
		# We want to cut `tolerance` off each end, to a minimum total length of `tolerance`
		magn = magnitude(tail, head)
		midpoint = magn / 2 # The midpoint of the input stroke
		magn -= 2*tolerance
		if magn < tolerance: magn = tolerance
		# `magn` is now the new length of the stroke
		# So move half `magn` in each direction from `midpoint`
		newtail = distalong(tail, head, midpoint-magn/2)
		newhead = distalong(tail, head, midpoint+magn/2)
		
		# Now the endpoints are determined
		self.head = head = newhead
		self.tail = tail = newtail
		
		# Calculate its AABB
		xlow = min(head.x, tail.x)
		xhigh = max(head.x, tail.x)
		ylow = min(head.y, tail.y)
		yhigh = max(head.y, tail.y)
		
		# Then ensure dx and dy are both >= `tolerance`, to avoid issues with some user error (two horizontal lines next to each other being seen as on different vertical levels)
		dx = xhigh - xlow
		dy = yhigh - ylow
		if dx < tolerance:
			xhigh += (tolerance-dx)/2
			xlow -= (tolerance-dx)/2
		if dy < tolerance:
			yhigh += (tolerance-dy)/2
			ylow -= (tolerance-dy)/2
		
		self.aabb = AABB(xlow, ylow, xhigh, yhigh)
		
		# And finally mark down its orientation so we don't have to calculate it later
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
	
	def strokify(self): # Convert into a Stroke object
		if self.orient == Orient.HORIZ: return Horizontal()
		elif self.orient == Orient.VERT: return Vertical()
		elif self.orient == Orient.UPDIAG: return Upward()
		elif self.orient == Orient.DOWNDIAG: return Downward()
		else: raise ValueError(self.orient)
	
	def rotated(self, theta): # Create a new Line that's this but rotated by `theta` radians
		cls = type(self) # Make sure we preserve the proper subclass
		return cls(rotate(self.head, theta), rotate(self.tail, theta))

class Divider(Line): # Acts like a normal line for parsing but does not appear in the output
	def strokify(self):
		return None

class DoubleLine(Line): # A normal stroke with a double head
	def strokify(self):
		stroke = super().strokify()
		return DoubleMod(stroke)

class TripleLine(Line): # As above
	def strokify(self):
		stroke = super().strokify()
		return TripleMod(stroke)

class HookLine(Line): # For Winkelhaken
	def strokify(self):
		return Winkelhaken()

class LineGroup:
	def __init__(self, children):
		self.children = list(children)
	
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
		
		for i, child in enumerate(self.children): # For each child…
			for j, bin in enumerate(bins): # …run through the bins…
				for other in bin: # …and for each bin, see if it conflicts with any element in that bin
					if child % other:
		#				print('Child', i, 'conflicts with bin', j)
						break
				else: # Didn't intersect with anything? Put it in this bin!
		#			print('Putting child', i, 'in bin', j)
					bin.append(child)
					break
			else: # Ran out of bins? Make a new one!
		#		print('Creating new bin', len(bins), 'for child', i)
				bins.append([child])
		
		return bins
	
	def rotated(self, theta): # Create a new LineGroup that's this but rotated
		cls = type(self) # In case we create more subclasses later
		return cls([c.rotated(theta) for c in self.children])
	
	def overall_angle(self): # Determine what angle this whole unit appears to be at
		def normalize(theta): # Bring all angles to the range [-pi/4, pi/4)
	#		while theta >= pi/4: theta -= pi/2
		#	print('Theta', theta, end=' ')
			while theta > 0: theta -= pi/2
		#	print('normalized to', theta)
			return theta
		angles = [normalize(c.angle) for c in self.children] # Get angles of all children
		avg = mean(angles)
	#	if avg > 0: avg -= pi/2 # Ensure it's always a counter-clockwise rotation, since that's what the TENU modifier does; a modification of pi/2 shouldn't change how well `untenu` works since our goal is to make it _ortho_normal
		# TODO why isn't this necessary? It actually breaks things when we draw something like this
		# \  /
		#  \ 
		#   \
		# Investigate this!
	#	print('Avg', avg)
		return avg
	
	def untenu(self): # Un-tenu this component if it only contains diagonals
		# Returns None if this isn't possible for one reason or another
		theta = -self.overall_angle()
		new = self.rotated(theta)
		if any(isinstance(c, HookLine) or c.orient.is_diagonal() for c in new.children): # Should not have any diagonal strokes or hakens inside a Tenu element!
			return None
		parsed = new.parse(already_rotated=True)
		if parsed is None: # Don't go into an infinite recursion!
			return None
		return Tenu(parsed)
	
	def parse(self, already_rotated=False):
		# First, check for a single stroke (or zero) as our base case
		if len(self.children) == 1:
			return self.children[0].strokify()
		if len(self.children) == 0:
			raise ValueError('Empty container')
		
		# First, check for tenu
		if all(c.orient.is_diagonal() for c in self.children):
			if already_rotated: return None # Avoid infinite regress - it's possible that no rotation will make this work!
			straightened = self.untenu()
			if straightened is not None: return straightened
		
		# Second, check for horizontal stack
		hdiv = self.try_to_divide(Orient.HORIZ)
		# Third, check for vertical stack
		vdiv = self.try_to_divide(Orient.VERT)
		
		if len(hdiv) > 1 and len(vdiv) > 1: # We could divide either way: need a heuristic to decide!
			pass # TODO - currently this results in the heuristic of "when in doubt, divide horizontally"
		
		if len(hdiv) > 1: # We can divide horizontally!
			return HStack( [LineGroup(g).parse() for g in hdiv] )
		
		if len(vdiv) > 1: # We can divide vertically!
			return VStack( [LineGroup(g).parse() for g in vdiv] )
		
		# Fourth, divide into non-intersecting components
		cdiv = self.partition()
		if len(cdiv) > 1: # We can form useful partitions!
			return Superpose( [LineGroup(g).parse() for g in cdiv] )
		
		# That last one should be guaranteed to succeed. If it doesn't, then something has gone very wrong.
		# This can happen for certain pathological arrangements of strokes, like this:
		# --- |
		#     |
		# |   |
		# |
		# | ---
		# But those never happen in actual cuneiform afaik
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
		self.children = [c for c in raw if c is not None]
class Stroke(Element):
	def process(self, raw):
		if raw: raise ValueError('Should be nothing', raw)
	def __str__(self): return self.sigil()
class StrokeMod(Element):
	def process(self, raw):
		if not isinstance(raw, Stroke): raise ValueError('Stroke needed', raw)
		self.child = raw
	def __str__(self): return str(self.child) + self.sigil()
class Modifier(Element):
	def process(self, raw):
		if not isinstance(raw, Composition): raise ValueError('Comp needed', raw)
		self.child = raw
	def __str__(self): return str(self.child) + self.sigil()
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
class Tenu(Modifier):
	def sigil(self): return 'TE' # Make all tenus larger as well as tilted
class DoubleMod(StrokeMod):
	def sigil(self): return '2'
class TripleMod(StrokeMod):
	def sigil(self): return '3'

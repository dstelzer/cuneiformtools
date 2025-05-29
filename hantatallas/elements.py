from enum import Enum
from math import sqrt, inf

empty = frozenset()

class ModeFlag(Enum): # Special flags to pass to certain algorithms
	GOTTSTEIN = 'g' # Treat downward diagonals and Winkelhakens the same when searching - specifically, make them all act as Winkelhakens, since those are the ones that have some special rules for normalization

class Modifier(Enum): # Modifiers that can be applied to strokes
	HEADSHORT = "'" # Single quote
	TAILSHORT = '"' # Double quote
	DOUBLE = '2'
	TRIPLE = '3'
	HIGHLIGHT = '!'
	INTERNAL_FLIP = '_I' # Multi-character name means it won't show up in parsing; this one's only used internally in the implementation of upward diagonal rendering
	INVERT = '?'
	DAMAGE = '#'
	INTERNAL_DIAGONAL = '_D' # As above
	INTERNAL_HEADLESS = '_H' # As above - indicates that the head of the stroke should not be drawn, for internal renderer reasons
	INTERNAL_BOTHWAYS = '_B' # As above - indicates that a head should be drawn at both ends of the stroke, like an amphisbaena, for internal renderer reasons

class Orientation(Enum): # The general shape of an element
	WIDE = 0
	TALL = 1
	NEITHER = 2
	MIXED = 3
	
	@classmethod
	def consensus(cls, seq):
		seq = list(seq) # We need to iterate over it multiple times
		if cls.MIXED in seq: return cls.MIXED
		if cls.WIDE in seq and cls.TALL in seq: return cls.MIXED
		if cls.WIDE in seq and not cls.TALL in seq: return cls.WIDE
		if cls.TALL in seq and not cls.WIDE in seq: return cls.TALL
		return cls.NEITHER

class Element:
	def can_expand_horizontally(self): return 0 # The amount of additional space this element wants
	def can_expand_vertically(self): return 0
	def kern_left(self): return 0 # The amount of space this element is willing to give up on each side
	def kern_right(self): return 0
	def kern_top(self): return 0
	def kern_bottom(self): return 0
	def allow_kern_leftward(self): return True # Should this element take up available space in this direction?
	def allow_kern_rightward(self): return True
	def allow_kern_upward(self): return True
	def allow_kern_downward(self): return True
	def orient(self): return Orientation.NEITHER
	def traverse(self): yield self # For tree traversal
	def size_factor(self): return 1 # How much space should this be given? Only overridden in Expand and Cursor, everything else uses 1
	
	def traverse_strokes(self):
		yield from (s for s in self.traverse() if isinstance(s, Stroke))
	def traverse_strokes_point(self, x, y): # May need to optimize this further: yield all strokes whose AABB includes the given point
		def aabb_includes_point(s):
			return s.pos[0] <= x <= s.pos[0]+s.dims[0] and s.pos[1] <= y <= s.pos[1]+s.dims[1]
		yield from (s for s in self.traverse_strokes() if aabb_includes_point(s))
	
	def add_modifier(self, mod): raise ValueError('Only strokes can have modifiers; you probably want an adjustment instead') # Stroke overrides this method
	
	def complexity(self): # Number of strokes within an element
		return sum(1 for e in self.traverse() if isinstance(e, Stroke))
	
	def _add_children(self, notes): # Add all descendant strokes to notes (utility method)
		for elem in self.traverse():
			if isinstance(elem, Stroke):
				notes.add(elem.ident)
	def _remove_children(self, notes): # The opposite of above
		for elem in self.traverse():
			if isinstance(elem, Stroke):
				notes.discard(elem.ident)

class CanvasShape(Enum):
	PORTRAIT = 'P'
	LANDSCAPE = 'L'
	SQUARE = 'S'
	WIDE = 'W'
	FUNCTIONAL = '_F' # This one isn't represented by a single character so it'll never show up in parsing; it's used to indicate a "functional form" designed to make comparisons easy rather than to look nice
	NARROW = 'N'
	XWIDE = 'X'

MAXIMUM_HEAD_SIZE = 1/3

PASS_LIMIT = 20 # Avoid an infinite loop in one routine

class Canvas(Element):
	def __init__(self, shape, internal, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.shape = CanvasShape(shape)
		self.internal = internal
	
	def __str__(self):
		return f'{self.shape.value} {self.internal}'
	
	def propagate_dimensions(self, unused1=None, unused2=None): # The parameters are for consistency with how other elements do dimensional propagation, but they're completely ignored here
		# (For other elements, it's ((w, h), (x, y)) where x,y is the top left corner)
		if self.shape == CanvasShape.SQUARE: self.dims = (1, 1)
		elif self.shape == CanvasShape.PORTRAIT: self.dims = (2/3, 1)
		elif self.shape == CanvasShape.LANDSCAPE: self.dims = (3/2, 1)
		elif self.shape == CanvasShape.WIDE: self.dims = (2, 1)
		elif self.shape == CanvasShape.FUNCTIONAL: self.dims = (1, 1) # For debugging; functional forms aren't meant to look pretty
		elif self.shape == CanvasShape.NARROW: self.dims = (1/3, 1)
		elif self.shape == CanvasShape.XWIDE: self.dims = (3, 1)
		
		self.internal.propagate_dimensions(self.dims, (0, 0))
	
	def draw(self, rend):
		self.internal.draw(rend)
	
	def traverse(self):
		yield self
		yield from self.internal.traverse()
	
	def functional_form(self, special=empty):
		return Canvas(CanvasShape.FUNCTIONAL, self.internal.functional_form(special))
	
	def __contains__(self, other): # This one just delegates
		if isinstance(other, Canvas):
			if other.shape != CanvasShape.FUNCTIONAL or self.shape != CanvasShape.FUNCTIONAL: raise ValueError('Only elements in functional form should be compared with `in`') # Sanity check
			return other.internal in self.internal
		else: return other in self.internal
	
	def apply_highlighting(self, ids): # Apply the HIGHLIGHT modifier to any strokes whose ident is listed in ids
		for elem in self.traverse():
			if isinstance(elem, Stroke) and elem.ident in ids:
				elem.add_modifier(Modifier.HIGHLIGHT)
	
	def highlight_containment(self, other, notes=None):
		if notes is None: notes = set()
		if isinstance(other, Canvas): self.internal.highlight_containment(other.internal, notes)
		else: self.internal.highlight_containment(other, notes)
		return notes
	
	def forest(self, tabs=0):
		return '\\begin{forest}\n' + self.internal.forest(tabs) + '\\end{forest}\n'

class Stroke(Element):
	def __init__(self, ident, mods=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.mods = mods or set()
		self.ident = ident # Used to identify this stroke for the highlighting features
		self.maximum_head_size = MAXIMUM_HEAD_SIZE # Allow this to be overridden later
	
	def __str__(self):
		return self._sigil() + ''.join(sorted(m.value for m in self.mods)) # Sort so that it's deterministic
	def _sigil(self): raise NotImplementedError() # Implement this in derived classes
	
	def add_modifier(self, mod):
		self.mods.add(Modifier(mod))
		if Modifier.DOUBLE in self.mods and Modifier.TRIPLE in self.mods:
			raise ValueError('A stroke cannot be both double and triple')
	
	def propagate_dimensions(self, dims, pos):
		self.dims = dims
		self.pos = pos
		self.adjust = 0,0
	
	def __contains__(self, other): # The `in` operator is used to test if one element is a sub-element of another; strokes don't contain anything, so for them it's just a test of equality
		# This method is expected to be used on functional forms, so modifiers don't matter
		# Note that any stroke matches a wildcard
		return isinstance(other, Stroke) and (type(other) == type(self) or type(other) == Wildcard)
	def highlight_containment(self, other, notes): # An extension to the above which is much less efficient but specifically notes which things have matched
		if other in self:
			notes.add(self.ident)
			return True
		else:
			return False
	
	def forest(self, tabs=0):
		mods = ''.join(sorted(m.value for m in self.mods))
		if mods: modcode = '}\\code{' + mods
		else: modcode = ''
		return '\t'*tabs + '[\\inlinesign{' + self._sigil() + modcode + '}]\n'

class Void(Stroke): # An emptiness that takes up space and does nothing else
	def __init__(self, *args, **kwargs):
		super().__init__(mods=None, *args, **kwargs)
	def _sigil(self): return '0'
	def draw(self, rend): rend.draw_void(*self.pos, *self.dims, self.mods) # Nothing to render normally - but if this has the "damaged" modifier, we should hatch in the whole area
	
	def _shrink_horizontal(self): return Modifier.HEADSHORT in self.mods
	def _shrink_vertical(self): return Modifier.TAILSHORT in self.mods
	def can_expand_horizontally(self): return 0 if self._shrink_horizontal() else inf
	def can_expand_vertically(self): return 0 if self._shrink_vertical() else inf
	def propagate_dimensions(self, dims, pos):
		w, h = dims
		x, y = pos
		ax, ay = 0, 0 # Adjustment
		if self._shrink_horizontal(): ax = w/2; x += w/2; w = 0
		if self._shrink_vertical(): ay = h/2; y += h/2; h = 0
		self.dims = (w, h)
		self.pos = (x, y)
		self.adjust = (ax, ay)
	
	def functional_form(self, special=empty): return None # Voids are ignored in functional form
	
	def forest(self, tabs=0): return '' # Don't include in forest

class Wildcard(Stroke): # A "stroke" that's used only for matching; it matches anything
	def _sigil(self): return '*'
	def draw(self, rend): rend.draw_wildcard(*self.pos, *self.dims, self.mods)
	def functional_form(self, special=empty): return Wildcard(self.ident)
	def __contains__(self, other): return False # Wildcards should only be on the right side of a comparison, not the left, so they're considered to match nothing (not even other wildcards)

class Cursor(Stroke): # A "stroke" that indicates where the cursor is placed in the text area when building signs. It takes up no space and is ignored in all comparisons.
	def _sigil(self): return '|'
	def allow_kern_leftward(self): return False
	def allow_kern_rightward(self): return False
	def allow_kern_downward(self): return False
	def allow_kern_upward(self): return False
	def draw(self, rend): rend.draw_cursor(*self.pos, *self.dims, self.mods)
	def functional_form(self, special=empty): return None # Remove from functional form
	def __contains__(self, other): raise ValueError('cursor should not be in search')
	def size_factor(self): return 0 # Take up no space at all

class Vertical(Stroke):
	def _sigil(self): return 'v'
	
	def can_expand_vertically(self): return inf
	def can_expand_horizontally(self): return max(0, self.maximum_head_size-self.dims[0])
	def propagate_dimensions(self, dims, pos):
		(w,h) = dims
		act = min(w, self.maximum_head_size)
		self.dims = (act, h)
		(x,y) = pos
		adj_x, adj_y = 0, 0
		if w > act: adj_x = (w-act)/2
		self.pos = (x+adj_x, y+adj_y)
		self.adjust = (adj_x, adj_y)
	def kern_left(self): return self.dims[0]/2
	def kern_right(self): return self.dims[0]/2
	def allow_kern_leftward(self): return False
	def allow_kern_rightward(self): return False
	def orient(self): return Orientation.TALL
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'b')
		rend.box(self.pos[0]-self.adjust[0], self.pos[1], self.adjust[0], self.dims[1], 'r')
		rend.draw_vertical(*self.pos, *self.dims, self.mods)
	
	def functional_form(self, special=empty):
		if Tenu in special: return DownDiag(self.ident, self.mods).functional_form(special-{Tenu}) # If this is in a tenu stack, treat it as a downward diagonal instead
		# Like with most strokes, we ignore most modifiers but turn doubling into a stack
		if Modifier.DOUBLE in self.mods: return VStack([Vertical(self.ident), Vertical(self.ident)])
		elif Modifier.TRIPLE in self.mods: return VStack([Vertical(self.ident), Vertical(self.ident), Vertical(self.ident)])
		else: return Vertical(self.ident)

class Horizontal(Stroke):
	def _sigil(self): return 'h'
	
	def can_expand_horizontally(self): return inf
	def can_expand_vertically(self): return max(0, self.maximum_head_size-self.dims[1])
	def propagate_dimensions(self, dims, pos):
		(w,h) = dims
		act = min(h, self.maximum_head_size)
		self.dims = (w, act)
		(x,y) = pos
		adj_x, adj_y = 0, 0
		if h > act: adj_y = (h-act)/2
		self.pos = (x+adj_x, y+adj_y)
		self.adjust = (adj_x, adj_y)
	def kern_top(self): return self.dims[1]/2
	def kern_bottom(self): return self.dims[1]/2
	def allow_kern_upward(self): return False
	def allow_kern_downward(self): return False
	def orient(self): return Orientation.WIDE
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'b')
		rend.box(self.pos[0], self.pos[1]-self.adjust[1], self.dims[0], self.adjust[1], 'r')
		rend.draw_horizontal(*self.pos, *self.dims, self.mods)
	
	def functional_form(self, special=empty):
		if Tenu in special: return UpDiag(self.ident, self.mods).functional_form(special-{Tenu}) # If this is in a tenu stack, treat it as a upward diagonal instead
		# Like with most strokes, we ignore most modifiers but turn doubling into a stack
		if Modifier.DOUBLE in self.mods: return HStack([Horizontal(self.ident), Horizontal(self.ident)])
		elif Modifier.TRIPLE in self.mods: return HStack([Horizontal(self.ident), Horizontal(self.ident), Horizontal(self.ident)])
		else: return Horizontal(self.ident)

class UpDiag(Stroke):
	def _sigil(self): return 'u'
	
	def can_expand_vertically(self): return inf
	def can_expand_horizontally(self): return inf
	def orient(self): return Orientation.WIDE # Diagonals "act" wide more than they "act" tall, in my experience
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'b')
		rend.draw_upward(*self.pos, *self.dims, self.mods)
	
	def functional_form(self, special=empty):
		# There's no diagonal stacking so we use HStack instead, since that becomes an "upward diagonal stack" when tenu
		if Modifier.DOUBLE in self.mods: return HStack([UpDiag(self.ident), UpDiag(self.ident)])
		elif Modifier.TRIPLE in self.mods: return HStack([UpDiag(self.ident), UpDiag(self.ident), UpDiag(self.ident)])
		else: return UpDiag(self.ident)
	# TODO: Do double upward strokes actually exist? I don't think I've ever seen one; they're just included here for completeness.

class DownDiag(Stroke):
	def _sigil(self): return 'd'
	
	def can_expand_vertically(self): return inf
	def can_expand_horizontally(self): return inf
	def orient(self): return Orientation.WIDE # Diagonals "act" wide more than they "act" tall, in my experience
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'b')
		rend.draw_downward(*self.pos, *self.dims, self.mods)
	
	def functional_form(self, special=empty):
		# This is where the GOTTSTEIN flag matters - it replaces downward diagonals with Winkelhakens
		cls = Winkelhaken if ModeFlag.GOTTSTEIN in special else DownDiag
		# (This wasn't intentional, because I didn't know about Gottstein's encoding when I was building the original system, but it's kind of cute that the code for a Winkelhaken is `c` just like Gottstein's code for a down diag)
		
		# There's no diagonal stacking so we use VStack instead, since that becomes a "downward diagonal stack" when tenu
		if Modifier.DOUBLE in self.mods: return VStack([cls(self.ident), cls(self.ident)])
		elif Modifier.TRIPLE in self.mods: return VStack([cls(self.ident), cls(self.ident), cls(self.ident)])
		else: return cls(self.ident)

class Winkelhaken(Stroke):
	def _sigil(self): return 'c'
	
	def _scaling(self):
		# The HEADSHORT and TAILSHORT modifiers don't make sense for the Winkelhaken, which has no head or tail. So they're repurposed to instead make the whole thing smaller.
		if Modifier.HEADSHORT in self.mods and Modifier.TAILSHORT in self.mods: return 1/3
		if Modifier.TAILSHORT in self.mods: return 1/2
		if Modifier.HEADSHORT in self.mods: return 2/3
		return 1
	
	def propagate_dimensions(self, dims, pos):
		s = self._scaling()
		(w,h) = dims
		adj_x, adj_y = 0, 0
		new_w = min(w, h/2) * s
		new_h = min(h, 2*w) * s
		
		self.dims = (new_w, new_h)
		(x,y) = pos
		xmod, ymod = 0, 0
		if w > new_w: adj_x = (w-new_w)/2
		if h > new_h: adj_y = (h-new_h)/2
		self.pos = (x+adj_x, y+adj_y)
		self.adjust = (adj_x, adj_y)
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'b')
		rend.box(self.pos[0]-self.adjust[0], self.pos[1], self.adjust[0], self.dims[1], 'r')
		rend.box(self.pos[0], self.pos[1]-self.adjust[1], self.dims[0], self.adjust[1], 'r')
		rend.draw_hook_wrapper(*self.pos, *self.dims, self.mods)
	
	def functional_form(self, special=empty): return Winkelhaken(self.ident) # No mods to worry about

class Container(Element):
	def __init__(self, contents=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if contents is None: contents = []
		self.contents = contents
	
	def can_expand_horizontally(self): return max(e.can_expand_horizontally() for e in self.contents)
	def can_expand_vertically(self): return max(e.can_expand_vertically() for e in self.contents)
	def orient(self): return Orientation.consensus(e.orient() for e in self.contents)
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'g')
		for each in self.contents: each.draw(rend)
	
	def traverse(self): # Classic preorder tree traversal
		yield self
		for each in self.contents:
			yield from each.traverse()
	
	def clean_intersections(self): # Pull intersecting elements out as far as possible, to deal with the ambiguities in superpositioning
		# Are all our non-superposed children pointed the same way?
		overall = Orientation.consensus(child.orient() for child in self.contents if not isinstance(child, Superpose))
		if overall == Orientation.NEITHER or overall == Orientation.MIXED: return self # Don't do this if there's no clear orientation
		def conflicts(o): return o != overall and o != Orientation.MIXED
		opposite = Orientation.TALL if overall==Orientation.WIDE else Orientation.WIDE # Whichever is the opposite of `overall`
		
		outer_elements = []
		for i, child in enumerate(self.contents):
			if isinstance(child, Superpose) and child.pulldir != overall:
				# child.pulldir indicates whether we've already pulled something out in some direction - in which case we shouldn't also pull something out in the *other* direction
				# Consider for example TA: we should pull the two vertical tacks outward, so that they go through all of the horizontals, but we shouldn't then pull the horizontals out to go through the right-hand vertical
				good = [e for e in child.contents if not conflicts(e.orient())]
				bad = [e for e in child.contents if conflicts(e.orient())]
				if bad: # We need to make a change
					self.contents[i] = Superpose(good, pulldir=child.pulldir)
					outer_elements.extend(bad)
		
		if not outer_elements: return self # No changes necessary
		# Otherwise, though, we need to put these "pulled-out" elements in superposition with the whole container
		outer_elements.append(self)
		return Superpose(outer_elements, pulldir=opposite).functional_form() # Gotta do the functional cleanup all over again just in case
	
	def _match_contents(self, other): # Utility method used by the __contains__ implementation in HStack and VStack
		outer, inner = self.contents, other.contents
		cls = type(self)
		matched = 0
		for each in outer:
#			print('Considering outer:', str(each))
			if any(isinstance(descendant, cls) for descendant in each.traverse()): # This one has a relevant container as a descendant, so we should check for sub-sequences
#				print('\tIt has descendant of class', cls)
				# So let's see if some sub-sequence of our whole sequence is contained (to deal with instances where there's an HStack nested somewhere inside an HStack etc)
				for end in range(len(inner), matched, -1): # Take progressively shorter sub-sequences
#					print('\t\tConsidering range', matched, 'to', end)
					subseq = cls(inner[matched:end]) # [matched:end], [matched:end-1], etc
					if subseq in each:
						matched = end
#						print('\t\t\tSuccess!', matched)
						break
				else: # We didn't find any sub-sequence, so let's test for a single element's containment instead
#					print('\t\tRanges did not succeed')
					if inner[matched] in each:
						matched += 1
#						print('\t\t\tBut single element containment did')
			else: # No descendants of the same class, so we don't have to bother checking sub-sequences
				if inner[matched] in each:
					matched += 1
#					print('\tSingle element containment worked', matched)
			if matched >= len(inner): return True
		return False
	def _match_contents_highlight(self, other, notes): # Less-efficient version of above that specifically keeps track of what things have matched for later highlighting
		outer, inner = self.contents, other.contents
		cls = type(self)
		matched = 0
		for each in outer:
			if any(isinstance(descendant, cls) for descendant in each.traverse()):
				for end in range(len(inner), matched, -1):
					subseq = cls(inner[matched:end])
					if each.highlight_containment(subseq, notes):
						matched = end
						break
				else:
					if each.highlight_containment(inner[matched], notes):
						matched += 1
			else:
				if each.highlight_containment(inner[matched], notes):
					matched += 1
			if matched >= len(inner): return True
		self._remove_children(notes)
		return False
	
	def kerning_and_arrangement(self, dims, pos, horizontal): # This is the special arrangement code for HStack and VStack, unified here based on the "horizontal" parameter
		# So instead of w/h we have "j" (direction of stacking) and "k" (opposite direction)
		# And instead of x/y we have "u" (direction of stacking) and "v" (opposite direction)
		def propagate_child(child, j, k, u, v):
			if horizontal: child.propagate_dimensions((j, k), (u, v))
			else: child.propagate_dimensions((k, j), (v, u))
			child._tmpj = j # For later reference
		def can_expand(child):
			if horizontal: return child.can_expand_horizontally()
			else: return child.can_expand_vertically()
		def allow_kern_back(child):
			if horizontal: return child.allow_kern_leftward()
			else: return child.allow_kern_upward()
		def allow_kern_front(child):
			if horizontal: return child.allow_kern_rightward()
			else: return child.allow_kern_downward()
		def kern_back(child):
			if horizontal: return child.kern_left()
			else: return child.kern_top()
		def kern_front(child):
			if horizontal: return child.kern_right()
			else: return child.kern_bottom()
		
		self.dims = dims
		self.pos = pos
		if horizontal: (j, k), (u, v), (jd, kd) = dims, pos, (0, 1)
		else: (k, j), (v, u), (kd, jd) = dims, pos, (0, 1)
		self.adjust = 0,0
		
		pieces = sum(c.size_factor() for c in self.contents)
	#	pieces = len(self.contents) + sum(c.factor()-1 for c in self.contents if isinstance(c, Expand)) - sum(1 for c in self.contents if isinstance(c, Cursor)) # The number of pieces, plus (factor-1) for each Expand adjustment we find, minus 1 for each Cursor (since those take no space)
		if pieces == 0: pieces = 1 # Prevent divide by zero when cursor but no other strokes
		each_j = j/pieces
		i = 0
		# First pass: just divide up the space evenly (with more space for Expands and less space for Cursors based on their size_factor)
		for each in self.contents:
			propagate_child(each, each_j*each.size_factor(), k, u+i*each_j, v)
			i += each.size_factor()
	#		if isinstance(each, Cursor):
	#			propagate_child(each, 0, k, u+i*each_j, v)
	#		elif isinstance(each, Expand):
	#			propagate_child(each, each_j*each.factor(), k, u+i*each_j, v)
	#			i += each.factor()
	#		else:
	#			propagate_child(each, each_j, k, u+i*each_j, v)
	#			i += 1
		
		# Now iteratively try to reclaim and reapportion space (if elements aren't using it or can kern into it)
		# We loop until nothing can expand, or no space can be reclaimed
		
		# Precision variable - don't bother making any changes if they're smaller than this
		epsilon = 1e-4
		passes = 0
		
		while True: # Now we go through an iterative process, reclaiming any available space, redistributing it, and repeating as necessary.
			# The first step: figuring out how much space can be reclaimed, and where it should be put.
	#		print('.', end='', flush=True)
			for each in self.contents: each._tmpgrow = 0 # Scratch variable
			dirty = False # Do we need to recalculate anything?
			while True:
				wanting = sum(1 for each in self.contents if can_expand(each)-each._tmpgrow > epsilon) # Count how many elements want more space
				if not wanting: break # Nothing that wants more space, don't bother
				
				fixed_space = 0
				kerns = 0
				for i, each in enumerate(self.contents):
					used = each.dims[jd] + each._tmpgrow # Space used + space newly allocated
					if i-1 >= 0 and allow_kern_back(each): # This element can be kerned backward to save some space
						used -= kern_front(self.contents[i-1])
						if kern_front(self.contents[i-1]): kerns += 1 # TODO ugly
					if i+1 < len(self.contents) and allow_kern_front(each): # This element can be kerned forward to save some more space
						used -= kern_back(self.contents[i+1])
						if kern_back(self.contents[i+1]): kerns += 1
					if used < 0: used = 0 # No glyph can take less than zero spce, regardless of kerning
					fixed_space += used
				flexible_space = j - fixed_space
				if flexible_space <= epsilon: break # No space available to work with
				remaining_space = flexible_space
				
				portion = flexible_space / wanting # Tentatively divide the available space evenly between the elements that want it
				found = False # Then check if any element specifically wants *less* than this
				for each in self.contents:
					grow = can_expand(each) - each._tmpgrow
					if epsilon < grow < portion:
						found = True
						each._tmpgrow += grow # Assign how much space we're going to give this one
						remaining_space -= grow
						dirty = True
				if not found: # There was nothing that wanted less than we had, so divide the remaining space between all of them equally
					for each in self.contents:
						if can_expand(each) - each._tmpgrow > epsilon:
							each._tmpgrow += portion
							remaining_space -= portion
							dirty = True
			
			if not dirty: break # Nothing was able to be repositioned
		#	if passes > 1: break
			
			# The second step: repositioning the elements based on this reallocated space
			current_position = u
			hacked_kerning = remaining_space / kerns if kerns else 0 # If there was some space that couldn't be used by flexible elements, give it back by expanding each kerning slightly
			# (But if there were no kerns, don't divide by zero)
			next_back_kerning = 0
			for i, each in enumerate(self.contents):
				back_kerning = next_back_kerning # We have to note this *before* reallocating space because that might change the kerning values! The updated values will get noted on the next pass through the big optimization loop
				next_back_kerning = kern_front(each) # So we record the back_kerning value here (for *this* element), before we reallocate its space, and then use this value in the next iteration of the loop
				front_kerning = kern_back(self.contents[i+1]) if i+1<len(self.contents) else 0 # The kerning available in front of this element - this one doesn't need to be calculated in advance because self.contents[i+1] hasn't been reallocated yet at this time
				previous_position = current_position
				current_position -= each.adjust[jd] # If the element adjusted its own position, we need to take that into account when assigning its new coordinates
				
				if each._tmpgrow:
					new_j = each.dims[jd] + each._tmpgrow
				else:
					# The amount of space allotted on the first pass (since this doesn't change for fixed elements)
					new_j = each._tmpj
				
				# Check for an edge case involving the available kerning exceeding the size of the element
				# When this happens, we want to center the element in the available kerning space, rather than letting it fall to the left edge (by default)
				# We don't have to worry about excessive kerning causing actual problems because we ensure current_position never moves backward, so this is purely an aesthetic thing
				if allow_kern_back(each) and allow_kern_front(each) and back_kerning+front_kerning > new_j:
					space = back_kerning + front_kerning - new_j
					back_kerning -= space/2
					front_kerning -= space/2
				
				if back_kerning and allow_kern_back(each): # Kern backwards the appropriate amount
		#			print(f'Kerning between {self.contents[i-1]} and {each}: {back_kerning}')
		#			print(f'{current_position}')
					current_position -= (back_kerning - hacked_kerning)
		#			print(f'{current_position}')
				
				new_u = current_position
				propagate_child(each, new_j, k, new_u, v)
				current_position += each.dims[jd] # Major bug fixed here! This must be used space not allocated space!
				current_position += each.adjust[jd]
				
				if front_kerning and allow_kern_front(each): # Finally, check to see if we need to adjust the kerning for the *next* element
					current_position -= (front_kerning - hacked_kerning)
				if previous_position > current_position: # But don't allow any element to take less than zero width
					current_position = previous_position
			
			passes += 1
			# Now loop back and check again
			# But as a failsafe:
			if passes > PASS_LIMIT: # This should never be necessary, but we don't want to crash
				print('WARNING: PASS_LIMIT REACHED')
				break
		
		# Once we've done all the positioning, we see if there's any vertical space we can give up to other elements on the next level up
		largest_k = max(each.dims[kd] for each in self.contents)
		adjust_v = min(each.adjust[kd] for each in self.contents)
		if horizontal:
			self.dims = (j, largest_k)
			self.adjust = (0, adjust_v)
		else:
			self.dims = (largest_k, j)
			self.adjust = (adjust_v, 0)
	
	def forest(self, tabs=0):
		lines = [child.forest(tabs+1) for child in self.contents]
		return ( '\t'*tabs + '[\\inlinesign{' + self.forestname() + '}\n'
				+ ''.join(lines)
				+ '\t'*tabs + ']\n' )

class HStack(Container):
	def __str__(self):
		return '[' + ','.join(str(c) for c in self.contents) + ']'
	def forestname(self): return 'hstack'
	
	def propagate_dimensions(self, dims, pos): return self.kerning_and_arrangement(dims, pos, horizontal=True)
	def kern_left(self): return self.contents[0].kern_left()
	def kern_right(self): return self.contents[-1].kern_right()
	def allow_kern_leftward(self): return self.contents[0].allow_kern_leftward()
	def allow_kern_rightward(self): return self.contents[-1].allow_kern_rightward()
	def kern_top(self): return min(c.kern_top() for c in self.contents)
	def kern_bottom(self): return min(c.kern_bottom() for c in self.contents)
	def allow_kern_upward(self): return all(c.allow_kern_upward() for c in self.contents)
	def allow_kern_downward(self): return all(c.allow_kern_downward() for c in self.contents)
	
	def functional_form(self, special=empty):
		newspecial = special - {VStack} # Indicate that the current processing is NOT happening inside a VStack, which matters for a certain type of ambiguity
		
		# Now here's where things get complicated!
		# First, take the functional form of each child
		raw_children = [c.functional_form(newspecial) for c in self.contents]
		children = []
		# Then go through and check some things
		for child in raw_children:
			if child is None: continue # Skip over blanks
			elif isinstance(child, HStack) and not isinstance(child, AmbigStack): children.extend(child.contents) # Flatten out nested HStacks
			else: children.append(child)
		if len(children) == 1:
			# If we only have one child, don't bother with a container
			return children[0]
		if not children:
			# If we have *no* children, return nothing
			return None
		
		# This extra complication is imported from VStack and is used in one specific case to resolve ambiguity in a way that leads to fewer overall stacks
		# See VStack.functional_form for details
		if all(isinstance(child, VStack) for child in children) and VStack in special:
			l = len(children[0].contents)
			if all(len(child.contents)==l for child in children):
				# So now we know that we've got an HStack of VStacks
				# And that all those VStacks are the same size
				# So, time to change that around
				child_contents = [child.contents for child in children]
				new_contents = list(zip(*child_contents))
				new_stacks = [HStack(list(c)) for c in new_contents]
				new_parent = VStack(new_stacks)
				# Then we re-functionalize this in case there are any new nesting issues that need to be handled
				return new_parent.functional_form(special-{Tenu}) # Note that we specifically use `special` rather than `newspecial` here because we want this evaluated in the same context that we were evaluated in!
				# Don't re-apply the Tenu modifier when re-functionalizing though - we've already converted cardinal strokes into diagonals, we don't want to do that again
		
		return HStack(children).clean_intersections()
	
	def __contains__(self, other):
		if any((other in child) for child in self.contents): return True
		if isinstance(other, HStack) and self._match_contents(other): return True
		return False
	def highlight_containment(self, other, notes): # Less-efficient version of the above that also highlights matches
		for child in self.contents:
			if child.highlight_containment(other, notes):
				return True
			child._remove_children(notes)
		if isinstance(other, HStack):
			return self._match_contents_highlight(other, notes)
		return False

class VStack(Container):
	def __str__(self):
		return '{' + ','.join(str(c) for c in self.contents) + '}'
	def forestname(self): return 'vstack'
	
	def propagate_dimensions(self, dims, pos): return self.kerning_and_arrangement(dims, pos, horizontal=False)
	def kern_top(self): return self.contents[0].kern_top()
	def kern_bottom(self): return self.contents[-1].kern_bottom()
	def allow_kern_upward(self): return self.contents[0].allow_kern_upward()
	def allow_kern_downward(self): return self.contents[-1].allow_kern_downward()
	def kern_left(self): return min(c.kern_left() for c in self.contents)
	def kern_right(self): return min(c.kern_right() for c in self.contents)
	def allow_kern_leftward(self): return all(c.allow_kern_leftward() for c in self.contents)
	def allow_kern_rightward(self): return all(c.allow_kern_rightward() for c in self.contents)
	
	def functional_form(self, special=empty):
		newspecial = special | {VStack} # Indicate that the current processing is happening inside a VStack, which matters for a certain type of ambiguity (see below)
		
		# This is mostly the same as HStack's implementation
		# But with one additional complication
		raw_children = [child.functional_form(newspecial) for child in self.contents]
		children = []
		for child in raw_children:
			if child is None: continue
			elif isinstance(child, VStack) and not isinstance(child, AmbigStack): children.extend(child.contents)
			else: children.append(child)
		if len(children) == 1:
			return children[0]
		if not children:
			return None
		
		# Here's the extra complication mentioned above!
		# Sometimes there's an ambiguity where something can be written either as HStacks of VStacks, or as VStacks of HStacks. (Consider, for example, the ZA sign.)
		# In this case, we need to choose one of the two to be canonical (to avoid search failures), and we chose an HStack of VStacks.
		# So if we see a VStack of HStacks, we need to change that.
		# EXCEPTION: If we're *within* a VStack, we choose instead to make a VStack of HStacks, so the total number of stacks can be reduced. We indicate this by having `VStack` included in `special` if we're processing the inside of a VStack.
		if all(isinstance(child, HStack) for child in children) and VStack not in special:
			l = len(children[0].contents) # We also know that `children` is not empty (because that case would have been handled above) so we can do this safely
			if all(len(child.contents)==l for child in children):
				# So now we know that we've got a VStack of HStacks
				# And that all those HStacks are the same size
				# So, time to change that around
				child_contents = [child.contents for child in children]
				new_contents = list(zip(*child_contents))
				new_stacks = [VStack(list(c)) for c in new_contents]
				new_parent = HStack(new_stacks)
	#			print('Fixed stacking', new_parent)
				# Then we re-functionalize this in case there are any new nesting issues that need to be handled
				return new_parent.functional_form(special-{Tenu}) # Note that we specifically use `special` rather than `newspecial` here because we want this evaluated in the same context that we were evaluated in!
				# Don't re-apply the Tenu modifier when re-functionalizing though - we've already converted cardinal strokes into diagonals, we don't want to do that again
		
		# We've added a second extra complication now, for signs like TI: when an [hc] HStack appears inside a VStack, it's not clear where the c belongs. We choose to change {h[hc]h} to [{hhh}c] for normalization purposes.
		lefts = [] # The of c's we see at the left edge
		rights = [] # The c's we see at the right edge
		for i, child in enumerate(children):
			if isinstance(child, HStack) and any(isinstance(c, Horizontal) for c in child.traverse_strokes()): # The child is an HStack which contains a horizontal
	#			print('Suitable child', i, child)
				if isinstance(child.contents[0], Winkelhaken):
					lefts.append(child.contents[0]) # Add it to our left list
					child.contents.pop(0) # And remove it from the child
	#				print('Removed left', child)
				if isinstance(child.contents[-1], Winkelhaken):
					rights.append(child.contents[-1])
					child.contents.pop(-1) # Likewise
	#				print('Removed right', child)
		if lefts or rights:
			new_parent = HStack([
				VStack(lefts),
				VStack(children),
				VStack(rights),
			])
	#		print('Lefts', lefts, 'Center', children, 'Rights', rights)
	#		print('Complete', new_parent)
	#		input()
			return new_parent.functional_form(special-{Tenu,VStack}) # As above we re-functionalize in case this change led to new things that need fixing; we specifically omit the Tenu modifier when we do, because that one would be bad to apply twice, and also omit VStack, because this has now become an HStack instead (this avoids an infinite loop that happens for things like {h[{cc}{hh}{hh}]h}; this step and the "rearrange stacks within stacks" step would go back and forth forever)
		
		return VStack(children).clean_intersections()
	
	def __contains__(self, other):
		if any((other in child) for child in self.contents): return True
		if isinstance(other, VStack) and self._match_contents(other): return True
		return False
	def highlight_containment(self, other, notes): # Less-efficient version of the above that also highlights matches
		for child in self.contents:
			if child.highlight_containment(other, notes):
				return True
			child._remove_children(notes)
		if isinstance(other, VStack):
			return self._match_contents_highlight(other, notes)
		return False

class AmbigStack(HStack, VStack): # A new experiment: a stack that acts as both HStack and VStack for comparison purposes
	def __str__(self): # We use weird brackets because people are never expected to code this explicitly
		return '⟦' + ','.join(str(c) for c in self.contents) + '⟧'
	def forestname(self): return 'ambigstack'
	# Other behavior is basically just inherited from HStack
	# We only have to override this one method to call the appropriate class constructor
	# But it can be much simpler, since an AmbigStack should never contain stacks
	def functional_form(self, special=empty):
		# First, take the functional form of each child
		raw_children = [c.functional_form(special) for c in self.contents]
		children = []
		# Then go through and check some things
		for child in raw_children:
			if child is None: continue # Skip over blanks
			elif isinstance(child, Container): raise ValueError('Container inside AmbigStack is not allowed') # Much simpler!
			else: children.append(child)
		if len(children) == 1:
			# If we only have one child, don't bother with a container
			return children[0]
		if not children:
			# If we have *no* children, return nothing
			return None
		return AmbigStack(children)
	
	# Rendering should only be needed in the UI, so we can be kind of hacky about it. The UI inserts a 0'" stroke at the end if it's supposed to render as a VStack, and otherwise it's supposed to render as an HStack.
	def propagate_dimensions(self, dims, pos):
		if isinstance(self.contents[-1], Void):
			return VStack.propagate_dimensions(self, dims, pos)
		else:
			return HStack.propagate_dimensions(self, dims, pos)
	
	# We shouldn't have to worry about __contains__, because AmbigStacks should always be on the *right* side of a containment operation (and multiclassing will take care of that, it's both an HStack and a VStack), but we might as well safety-proof this
	def __contains__(self, other): # This works the same as HStack and VStack except it checks both stack classes (which'll also catch AmbigStack as a subclass of them both)
		if any((other in child) for child in self.contents): return True
		if isinstance(other, (HStack, VStack)) and self._match_contents(other): return True
		return False
	def highlight_containment(self, other, notes): # Less-efficient version of the above that also highlights matches
		for child in self.contents:
			if child.highlight_containment(other, notes):
				return True
			child._remove_children(notes)
		if isinstance(other, (HStack, VStack)):
			return self._match_contents_highlight(other, notes)
		return False

class Superpose(Container):
	def __init__(self, *args, pulldir=Orientation.NEITHER, **kwargs):
		super().__init__(*args, **kwargs)
		self.pulldir = pulldir # Used in the functional-form calculations to make sure that we don't "pull out" elements in the wrong way
	
	def __str__(self):
		return '(' + ','.join(str(c) for c in self.contents) + ')'
	def forestname(self): return 'superpose'
	
	def propagate_dimensions(self, dims, pos):
		self.dims = dims
		self.pos = pos
		self.adjust = 0,0
		for child in self.contents: child.propagate_dimensions(dims, pos)
	
	def kern_left(self): return min(c.kern_left() for c in self.contents)
	def kern_right(self): return min(c.kern_right() for c in self.contents)
	def kern_top(self): return min(c.kern_top() for c in self.contents)
	def kern_bottom(self): return min(c.kern_bottom() for c in self.contents)
	def allow_kern_upward(self): return any(c.allow_kern_upward() for c in self.contents)
	def allow_kern_downward(self): return any(c.allow_kern_downward() for c in self.contents)
	def allow_kern_leftward(self): return any(c.allow_kern_leftward() for c in self.contents)
	def allow_kern_rightward(self): return any(c.allow_kern_rightward() for c in self.contents)
	# TODO: Should this be all instead of any?
	# Superposition is generally used for elements that intersect which means horizontal elements don't go all the way to the top/bot and vertical elements don't go all the way to the left/right
	# But adjust this if it causes problems
	def orient(self): return Orientation.NEITHER # Because they're handled specially in the orientation systems
	
	def functional_form(self, special=empty):
		newspecial = special - {VStack} # Indicate that the current processing is NOT happening inside a VStack, which matters for a certain type of ambiguity
		
		raw_children = [child.functional_form(newspecial) for child in self.contents]
		children = []
		for child in raw_children:
			if child is None: continue
			elif isinstance(child, Superpose):
				for grandchild in child.contents:
					children.append(grandchild)
			else:
				children.append(child)
		if len(children) == 1: return children[0]
		if not children: return None
		children.sort(key=str) # Sort by ASCII form - it's arbitrary but consistent
		return Superpose(children, pulldir=self.pulldir)
	
	def __contains__(self, other):
		if any((other in child) for child in self.contents): return True
		if isinstance(other, Superpose):
			# This part is kind of hacky. It tests whether each child of `other` can be found in a child of `self`, but doesn't check whether those children of `self` are distinct, because that runs into combinatorial explosion.
			# For example, by this algorithm, ([hvh]d) encompasses (hv), which is not ideal.
			# But superpositions are kind of messy anyway, so hopefully the false positives from this are worth not having any false negatives.
			for oc in other.contents:
				if not any(oc in child for child in self.contents): return False
			return True
		return False
	def highlight_containment(self, other, notes): # Less-efficient version of the above that also highlights matches
		for child in self.contents:
			if child.highlight_containment(other, notes):
				return True
			child._remove_children(notes)
		if isinstance(other, Superpose):
			for oc in other.contents:
				for child in self.contents:
					if child.highlight_containment(oc, notes):
						break # Skip the else-clause
				else: # There was no match
					self._remove_children(notes)
					return False
			return True
		self._remove_children(notes)
		return False

class Adjustment(Element):
	def __init__(self, child, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.child = child
	
	def __str__(self):
		return str(self.child) + self._sigil()
	
	def traverse(self):
		yield self
		yield from self.child.traverse()
	
	def functional_form(self, special=empty):
		# Adjustments are by default ignored in functional form
		return self.child.functional_form(special)
	
	def forest(self, tabs=0):
		return '\t'*tabs + '[\\code{' + self._sigil() + '}\n' + self.child.forest(tabs+1) + '\t'*tabs + ']\n'

class Tenu(Adjustment): # Rotate a container 45 degrees
	def _sigil(self): return 'T'
	def can_expand_horizontally(self): return self._potential - self.dims[0]
	def can_expand_vertically(self): return self._potential - self.dims[1]
	def kern_left(self): return self._leftmost
	def kern_right(self): return self.dims[0]-self._rightmost
	def kern_top(self): return self._topmost
	def kern_bottom(self): return self.dims[1]-self._bottommost
#	def allow_kern_downward(self): return self.kern_bottom()<0.05
#	def allow_kern_upward(self): return self.kern_top()<0.05
#	def allow_kern_leftward(self): return self.kern_left()<0.05
#	def allow_kern_rightward(self): return self.kern_right()<0.05
	def propagate_dimensions(self, dims, pos):
		(x,y) = pos
		(w,h) = dims
		d = min(dims)
		self._potential = max(dims) # Potential size
		self.adjust = (dx,dy) = (w-d)/2, (h-d)/2
		self.pos = (x+dx, y+dy)
		self.dims = (d, d)
		small = d*sqrt(2)/2 # This is the side length of the smaller, tilted square that forms the bounds of our child
		self.child.propagate_dimensions((small, small), (0, 0)) # Set position to (0,0) to make the rendering hack work better
		self._determine_extrema()
	def draw(self, rend):
		with rend.tenu(self.pos, self.dims): # Context manager that adjusts the coordinate system of the canvas for this one instance, then puts it back afterward
			self.child.draw(rend)
		rend.box(self.pos[0]+self._rightmost, self.pos[1], self.dims[0]-self._rightmost, self.dims[1], 'y') # Rightmost
		rend.box(self.pos[0], self.pos[1], self._leftmost, self.dims[1], 'y') # Leftmost
		rend.box(self.pos[0], self.pos[1]+self._bottommost, self.dims[0], self.dims[1]-self._bottommost, 'y') # Bottommost
		rend.box(self.pos[0], self.pos[1], self.dims[0], self._topmost, 'y') # Topmost
	def functional_form(self, special=empty): # This is where the special parameter gets used!
		return self.child.functional_form(special|{Tenu}) # Add the "Tenu" special modifier
	
	def _coordinate_transform(self, x, y):
		cs = sqrt(2)/2 # Since the rotation is always 45 degrees, cos and sin are both sqrt(2)/2
		# First, rotation matrix
		# x' =  x cos + y sin
		# y' = -x sin + y cos
		xx =  x*cs + y*cs
		yy = -x*cs + y*cs
		# Then, translate the origin
		yy += self.dims[1]/2 # By half the large square side length
		# (I.e. the distance between the small square's origin and the large square's origin)
		# Because the large square's origin is the top left corner, and the small square's origin is the left corner
		# +--+
		# |/\|
		# |\/|
		# +--+
		return xx, yy
	def _determine_extrema(self):
		strokes = [elem for elem in self.child.traverse() if type(elem) in {Horizontal, Vertical, DownDiag, UpDiag, Winkelhaken}]
		# Rightmost = southeast corner
		self._rightmost = max(
			self._coordinate_transform(
				stroke.pos[0]+stroke.dims[0], # east
				stroke.pos[1]+stroke.dims[1]  # south
			)[0] # x'
			for stroke in strokes
		)
		# Leftmost = northwest corner
		self._leftmost = min(
			self._coordinate_transform(
				stroke.pos[0], # west
				stroke.pos[1]  # north
			)[0] # x'
			for stroke in strokes
		)
		# Topmost = northeast corner
		self._topmost = min(
			self._coordinate_transform(
				stroke.pos[0]+stroke.dims[0], # east
				stroke.pos[1] # north
			)[1] # y'
			for stroke in strokes
		)
		# Bottommost = southwest corner
		self._bottommost = max(
			self._coordinate_transform(
				stroke.pos[0], # west
				stroke.pos[1]+stroke.dims[1] # south
			)[1] # y'
			for stroke in strokes
		)
		#print(self._rightmost, self._leftmost, self._topmost, self._bottommost)

class Expand(Adjustment): # Request twice as much space as usual from our parent
	# This class actually does basically nothing - but it's checked for in the kerning algorithm in VStack and HStack
	# Note that this prevents its child from expanding! It's meant to be used when an element doesn't ask for enough space, and expanding elements always ask for as much space as possible. So don't use this on an expanding element unless you want to give it a fixed size.
	def _sigil(self): return 'E'
	def size_factor(self): # How much expansion do we want?
		return 1 + self.child.size_factor()
	def can_expand_horizontally(self): return 0
	def can_expand_vertically(self): return 0
	def propagate_dimensions(self, dims, pos):
		self.dims, self.pos = dims, pos
		self.adjust = (0, 0)
		self.child.propagate_dimensions(dims, pos)
	def draw(self, rend): self.child.draw(rend)
	def orient(self): return self.child.orient()
	def kern_top(self): return self.child.kern_top()
	def kern_bottom(self): return self.child.kern_bottom()
	def kern_left(self): return self.child.kern_left()
	def kern_right(self): return self.child.kern_right()

class Margin(Adjustment): # Put a small margin around an element (for when signs are components of other signs)
	def _sigil(self): return 'M'
	def can_expand_horizontally(self): return self.child.can_expand_horizontally()
	def can_expand_vertically(self): return self.child.can_expand_vertically()
	def orient(self): return self.child.orient()
	def draw(self, rend): self.child.draw(rend)
	
	def propagate_dimensions(self, dims, pos):
		# First, we tell our child to fill in the whole space we're given, minus a margin around it
		w, h = dims
		x, y = pos
		self.margin = m = min(w/5, h/5, 0.1)
		self.child.propagate_dimensions((w-2*m, h-2*m), (x+m, y+m))
		# Then, we see what space it actually took up, and resize ourself to be that, plus a margin around it
		w, h = self.child.dims
		x, y = self.child.pos
		ax, ay = self.child.adjust
		self.dims = (w+2*m, h+2*m)
		self.pos = (x-m, y-m)
		self.adjust = (ax, ay)

class Restrict(Adjustment): # Prevent a component from expanding
	def _sigil(self): return 'R'
	def can_expand_horizontally(self): return 0
	def can_expand_vertically(self): return 0
	def draw(self, rend): self.child.draw(rend)
	def orient(self): return self.child.orient()
	def kern_top(self): return self.child.kern_top()
	def kern_bottom(self): return self.child.kern_bottom()
	def kern_left(self): return self.child.kern_left()
	def kern_right(self): return self.child.kern_right()
	def propagate_dimensions(self, dims, pos):
		self.dims, self.pos = dims, pos
		self.adjust = (0, 0)
		self.child.propagate_dimensions(dims, pos)

class Allow(Adjustment): # Allow a component to expand in any direction, regardless of what its children say
	def _sigil(self): return 'A'
	def can_expand_horizontally(self): return inf
	def can_expand_vertically(self): return inf
	
	def size_factor(self): # If this is wrapped around an E element, allow that to work too, as a special case (normally E must be outermost)
		return self.child.size_factor()
	
	def draw(self, rend): self.child.draw(rend)
	def orient(self): return self.child.orient()
	def kern_top(self): return self.child.kern_top()
	def kern_bottom(self): return self.child.kern_bottom()
	def kern_left(self): return self.child.kern_left()
	def kern_right(self): return self.child.kern_right()
	
	def propagate_dimensions(self, dims, pos):
		self.dims, self.pos = dims, pos
		self.adjust = (0, 0)
		self.child.propagate_dimensions(dims, pos)

class Kern(Adjustment): # Allow neighboring elements to kern into this one from every side, up to a maximum of half this element's dimension
	def _sigil(self): return 'K'
	def can_expand_horizontally(self): return self.child.can_expand_horizontally()
	def can_expand_vertically(self): return self.child.can_expand_vertically()
	def draw(self, rend): self.child.draw(rend)
	def orient(self): return self.child.orient()
	
	def kern_top(self): return self.dims[1]/2
	def kern_bottom(self): return self.dims[1]/2
	def kern_left(self): return self.dims[0]/2
	def kern_right(self): return self.dims[0]/2
	
	def propagate_dimensions(self, dims, pos):
		self.dims, self.pos = dims, pos
		self.adjust = (0, 0)
		self.child.propagate_dimensions(dims, pos)

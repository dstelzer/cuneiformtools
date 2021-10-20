from enum import Enum
from math import sqrt

class Modifier(Enum): # Modifiers that can be applied to strokes
	HEADSHORT = "'"
	TAILSHORT = '"'
	DOUBLE = '2'
	TRIPLE = '3'
	HIGHLIGHT = '!'
	INTERNAL_FLIP = '_I' # Multi-character name means it won't show up in parsing; this one's only used internally in the implementation of upward diagonal rendering
	INVERT = '?'

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
	def can_expand_horizontally(self): return False
	def can_expand_vertically(self): return False
	def kern_left(self): return 0
	def kern_right(self): return 0
	def kern_top(self): return 0
	def kern_bottom(self): return 0
	def allow_kern_leftward(self): return True
	def allow_kern_rightward(self): return True
	def allow_kern_upward(self): return True
	def allow_kern_downward(self): return True
	def orient(self): return Orientation.NEITHER
	def traverse(self): yield self # For tree traversal
	
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
	
	def functional_form(self):
		return Canvas(CanvasShape.FUNCTIONAL, self.internal.functional_form())
	
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

class Stroke(Element):
	def __init__(self, ident, mods=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.mods = mods or set()
		self.ident = ident # Used to identify this stroke for the highlighting features
	
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

class Void(Stroke): # An emptiness that takes up space and does nothing else
	def __init__(self, *args, **kwargs):
		super().__init__(mods=None, *args, **kwargs)
	def _sigil(self): return '0'
	def draw(self, rend): pass # Nothing to render
	
	def _shrink_horizontal(self): return Modifier.HEADSHORT in self.mods
	def _shrink_vertical(self): return Modifier.TAILSHORT in self.mods
	def can_expand_horizontally(self): return not self._shrink_horizontal()
	def can_expand_vertically(self): return not self._shrink_vertical()
	def propagate_dimensions(self, dims, pos):
		w, h = dims
		x, y = pos
		ax, ay = 0, 0 # Adjustment
		if self._shrink_horizontal(): ax = w/2; x += w/2; w = 0
		if self._shrink_vertical(): ay = h/2; y += h/2; h = 0
		self.dims = (w, h)
		self.pos = (x, y)
		self.adjust = (ax, ay)
	
	def functional_form(self): return None # Voids are ignored in functional form

class Wildcard(Stroke): # A "stroke" that's used only for matching; it matches anything
	def _sigil(self): return '*'
	def can_expand_horizontally(self): return False
	def can_expand_vertically(self): return False
	def draw(self, rend): rend.draw_wildcard(*self.pos, *self.dims, self.mods)
	def functional_form(self): return Wildcard(self.ident)
	def __contains__(self, other): return False # Wildcards should only be on the right side of a comparison, not the left, so they're considered to match nothing (not even other wildcards)

class Cursor(Stroke): # A "stroke" that indicates where the cursor is placed in the text area when building signs. It takes up no space and is ignored in all comparisons.
	def _sigil(self): return '|'
	def can_expand_horizontally(self): return False # TODO does anything care about all(can_expand_*)?
	def can_expand_vertically(self): return False
	def allow_kern_leftward(self): return False
	def allow_kern_rightward(self): return False
	def allow_kern_downward(self): return False
	def allow_kern_upward(self): return False
	def draw(self, rend): rend.draw_cursor(*self.pos, *self.dims, self.mods)
	def functional_form(self): return None # Remove from functional form
	def __contains__(self, other): raise ValueError('cursor should not be in search')

class Vertical(Stroke):
	def _sigil(self): return 'v'
	
	def can_expand_vertically(self): return True
	def propagate_dimensions(self, dims, pos):
		(w,h) = dims
		act = min(w, MAXIMUM_HEAD_SIZE)
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
	
	def functional_form(self):
		# Like with most strokes, we ignore most modifiers but turn doubling into a stack
		if Modifier.DOUBLE in self.mods: return VStack([Vertical(self.ident), Vertical(self.ident)])
		elif Modifier.TRIPLE in self.mods: return VStack([Vertical(self.ident), Vertical(self.ident), Vertical(self.ident)])
		else: return Vertical(self.ident)

class Horizontal(Stroke):
	def _sigil(self): return 'h'
	
	def can_expand_horizontally(self): return True
	def propagate_dimensions(self, dims, pos):
		(w,h) = dims
		act = min(h, MAXIMUM_HEAD_SIZE)
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
	
	def functional_form(self):
		# Like with most strokes, we ignore most modifiers but turn doubling into a stack
		if Modifier.DOUBLE in self.mods: return HStack([Horizontal(self.ident), Horizontal(self.ident)])
		elif Modifier.TRIPLE in self.mods: return HStack([Horizontal(self.ident), Horizontal(self.ident), Horizontal(self.ident)])
		else: return Horizontal(self.ident)

class UpDiag(Stroke):
	def _sigil(self): return 'u'
	
	def can_expand_vertically(self): return True
	def can_expand_horizontally(self): return True
	def orient(self): return Orientation.WIDE # Diagonals "act" wide more than they "act" tall, in my experience
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'b')
		rend.draw_upward(*self.pos, *self.dims, self.mods)
	
	def functional_form(self):
		# There's no diagonal stacking so we use HStack instead
		if Modifier.DOUBLE in self.mods: return HStack([UpDiag(self.ident), UpDiag(self.ident)])
		elif Modifier.TRIPLE in self.mods: return HStack([UpDiag(self.ident), UpDiag(self.ident), UpDiag(self.ident)])
		else: return UpDiag(self.ident)
	# TODO: Do double upward strokes actually exist? I don't think I've ever seen one; they're just included here for completeness.

class DownDiag(Stroke):
	def _sigil(self): return 'd'
	
	def can_expand_vertically(self): return True
	def can_expand_horizontally(self): return True
	def orient(self): return Orientation.WIDE # Diagonals "act" wide more than they "act" tall, in my experience
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'b')
		rend.draw_downward(*self.pos, *self.dims, self.mods)
	
	def functional_form(self):
		# There's no diagonal stacking so we use HStack instead
		if Modifier.DOUBLE in self.mods: return HStack([DownDiag(self.ident), DownDiag(self.ident)])
		elif Modifier.TRIPLE in self.mods: return HStack([DownDiag(self.ident), DownDiag(self.ident), DownDiag(self.ident)])
		else: return DownDiag(self.ident)

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
		rend.draw_hook(*self.pos, *self.dims, self.mods)
	
	def functional_form(self): return Winkelhaken(self.ident) # No mods to worry about

class Container(Element):
	def __init__(self, contents=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if contents is None: contents = []
		self.contents = contents
	
	def can_expand_horizontally(self): return any(e.can_expand_horizontally() for e in self.contents)
	def can_expand_vertically(self): return any(e.can_expand_vertically() for e in self.contents)
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
			if any(isinstance(descendant, cls) for descendant in each.traverse()): # This one has a relevant container as a descendant, so we should check for sub-sequences
				# So let's see if some sub-sequence of our whole sequence is contained (to deal with instances where there's an HStack nested somewhere inside an HStack etc)
				for end in range(len(inner), matched, -1): # Take progressively shorter sub-sequences
					subseq = cls(inner[matched:end]) # [matched:end], [matched:end-1], etc
					if subseq in each:
						matched = end
						break
				else: # We didn't find any sub-sequence, so let's test for a single element's containment instead
					if inner[matched] in each:
						matched += 1
			else: # No descendants of the same class, so we don't have to bother checking sub-sequences
				if inner[matched] in each:
					matched += 1
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

class HStack(Container):
	def __str__(self):
		return '[' + ','.join(str(c) for c in self.contents) + ']'
	
	def propagate_dimensions(self, dims, pos):
		self.dims = (w,h) = dims
		self.pos = (x,y) = pos
		self.adjust = 0,0
		pieces = len(self.contents) + sum(1 for c in self.contents if isinstance(c, Expand)) - sum(1 for c in self.contents if isinstance(c, Cursor)) # The number of pieces, plus 1 for each Expand adjustment we find, minus 1 for each Cursor (since those take no space)
		if pieces == 0: pieces = 1 # Prevent divide by zero when cursor but no other strokes
		each_w = w/pieces
		i = 0
		for each in self.contents:
			if isinstance(each, Cursor):
				each.propagate_dimensions((0, h), (x+i*each_w, y))
			elif isinstance(each, Expand):
				each.propagate_dimensions((each_w*2, h), (x+i*each_w, y))
				i += 2
			else:
				each.propagate_dimensions((each_w, h), (x+i*each_w, y))
				i += 1
		
		# Now check if we have to do any fancy kerning and recalculation
		if any(each.can_expand_horizontally() for each in self.contents):
			# In this case, we have different types of strokes together, and some of them can expand horizontally
			# So first we calculate how much space is currently used and can't be avoided
			fixed_space = 0
			for i, each in enumerate(self.contents):
				if each.can_expand_horizontally(): continue # Ignore flexible ones
				used = each.dims[0]
				# Can we kern this into its neighbors?
				if i-1 >= 0 and each.allow_kern_leftward():
					used -= self.contents[i-1].kern_right()
				if i+1 < len(self.contents) and each.allow_kern_rightward():
					used -= self.contents[i+1].kern_left()
				if used < 0: used = 0 # Even with kerning, the minimum space occupied by a glyph is 0
				fixed_space += used
			flexible_space = w - fixed_space
			portion = flexible_space / sum(1 for each in self.contents if each.can_expand_horizontally()) # Divide by the number of flexible elements
			
			# Now give them their new positions
			current_position = x
			for i, each in enumerate(self.contents):
				left_kerning = self.contents[i-1].kern_right() if i-1>=0 else 0
				right_kerning = self.contents[i+1].kern_left() if i+1<len(self.contents) else 0
				previous_position = current_position
				current_position -= each.adjust[0] # If the element adjusted its own position, we need to take that into account when assigning its new coordinates
				
				if isinstance(each, Expand):
					this_w = each_w*2
				elif isinstance(each, Cursor):
					this_w = 0
				else:
					this_w = each_w
				
				if each.can_expand_horizontally(): # This is a flexible one
					new_w = portion + left_kerning + right_kerning # The new width to assign
					new_x = current_position - left_kerning
					each.propagate_dimensions((new_w, h), (new_x, y))
					current_position += portion
					# current_position += each.adjust[0] # Flexible ones should never have adjustment values in the direction that they're flexible - they're expected to take up all the space they're given
				
				elif left_kerning and each.allow_kern_leftward(): # This one should be nudged to the left
					new_x = current_position - left_kerning
					each.propagate_dimensions((this_w, h), (new_x, y))
					# I'm not exactly sure why, but propagating the dimensions with the original width and height, and then applying the adjustment values, works better than propagating with the width and height stored in each.dims. So propagate(each.dims, (new_x, each.pos[1])) doesn't work, and this does.
					current_position += each.dims[0] - left_kerning
					current_position += each.adjust[0]
				
				else: # This one needs no special handling
					new_x = current_position
					each.propagate_dimensions((this_w, h), (new_x, y))
					current_position += each.dims[0]
					current_position += each.adjust[0]
				
				if right_kerning and each.allow_kern_rightward() and not each.can_expand_horizontally(): # Finally, check to see if we need to adjust the kerning for the *next* element
					current_position -= right_kerning
				if previous_position > current_position: # But don't allow any element to take less than zero width
					current_position = previous_position
		
		# Once we've done all the positioning, we see if there's any space we can give up to other elements (which might trigger this whole process all over again)
		largest_h = max(each.dims[1] for each in self.contents)
		adjust_y = min(each.adjust[1] for each in self.contents)
		self.dims = (w, largest_h)
		self.adjust = (0, adjust_y)
	
	def kern_left(self): return self.contents[0].kern_left()
	def kern_right(self): return self.contents[-1].kern_right()
	def allow_kern_leftward(self): return self.contents[0].allow_kern_leftward()
	def allow_kern_rightward(self): return self.contents[-1].allow_kern_rightward()
	def kern_top(self): return min(c.kern_top() for c in self.contents)
	def kern_bottom(self): return min(c.kern_bottom() for c in self.contents)
	def allow_kern_upward(self): return all(c.allow_kern_upward() for c in self.contents)
	def allow_kern_downward(self): return all(c.allow_kern_downward() for c in self.contents)
	
	def functional_form(self):
		# Now here's where things get complicated!
		# First, take the functional form of each child
		raw_children = [c.functional_form() for c in self.contents]
		children = []
		# Then go through and check some things
		for child in raw_children:
			if child is None: continue # Skip over blanks
			elif isinstance(child, HStack): children.extend(child.contents) # Flatten out nested HStacks
			else: children.append(child)
		if len(children) == 1:
			# If we only have one child, don't bother with a container
			return children[0]
		if not children:
			# If we have *no* children, return nothing
			return None
		
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
	
	def propagate_dimensions(self, dims, pos):
		self.dims = (w,h) = dims
		self.pos = (x,y) = pos
		self.adjust = 0,0
		pieces = len(self.contents) + sum(1 for c in self.contents if isinstance(c, Expand)) - sum(1 for c in self.contents if isinstance(c, Cursor)) # The number of pieces, plus 1 for each Expand adjustment we find, minus 1 for each Cursor (since those take no space)
		if pieces == 0: pieces = 1 # Prevent divide by zero
		each_h = h/pieces
		i = 0
		for each in self.contents:
			if isinstance(each, Cursor):
				each.propagate_dimensions((w, 0), (x, y+i*each_h))
			elif isinstance(each, Expand):
				each.propagate_dimensions((w, each_h*2), (x, y+i*each_h))
				i += 2
			else:
				each.propagate_dimensions((w, each_h), (x, y+i*each_h))
				i += 1
		
		# Now check if we have to do any fancy kerning and recalculation
		if any(each.can_expand_vertically() for each in self.contents):
			# The algorithm is the same as for horizontal, so see HStack for details
			fixed_space = 0
			for i, each in enumerate(self.contents):
				if each.can_expand_vertically(): continue # Ignore flexible ones
				used = each.dims[1]
				# Can we kern this into its neighbors?
				if i-1 >= 0 and each.allow_kern_upward():
					used -= self.contents[i-1].kern_bottom()
				if i+1 < len(self.contents) and each.allow_kern_downward():
					used -= self.contents[i+1].kern_top()
				if used < 0: used = 0 # Even with kerning, the minimum space occupied by a glyph is 0
				fixed_space += used
			flexible_space = h - fixed_space
			portion = flexible_space / sum(1 for each in self.contents if each.can_expand_vertically()) # Divide by the number of flexible elements
			
			# Now give them their new positions
			current_position = y
			for i, each in enumerate(self.contents):
				top_kerning = self.contents[i-1].kern_bottom() if i-1>=0 else 0
				bottom_kerning = self.contents[i+1].kern_top() if i+1<len(self.contents) else 0
				previous_position = current_position
				current_position -= each.adjust[1] # If the element adjusted its own position, we need to take that into account when assigning its new coordinates
				
				if isinstance(each, Expand):
					this_h = 2*each_h
				elif isinstance(each, Cursor):
					this_h = 0
				else:
					this_h = each_h
				
				if each.can_expand_vertically(): # This is a flexible one
					new_h = portion + top_kerning + bottom_kerning # The new height to assign
					new_y = current_position - top_kerning
					each.propagate_dimensions((w, new_h), (x, new_y))
					current_position += portion
					# See HStack for justification
				
				elif top_kerning and each.allow_kern_upward(): # This one should be nudged upward
					new_y = current_position - top_kerning
					each.propagate_dimensions((w, this_h), (x, new_y))
					# As above
					current_position += each.dims[1] - top_kerning
					current_position += each.adjust[1]
				
				else: # This one needs no special handling
					new_y = current_position
					each.propagate_dimensions((w, this_h), (x, new_y))
					current_position += each.dims[1]
					current_position += each.adjust[1]
				
				if bottom_kerning and each.allow_kern_downward() and not each.can_expand_vertically(): # Finally, check to see if we need to adjust the kerning for the *next* element
					current_position -= bottom_kerning
				if previous_position > current_position: # But don't allow any element to take less than zero height
					current_position = previous_position
		
		# Once we've done all the positioning, we see if there's any space we can give up to other elements (which might trigger this whole process all over again)
		largest_w = max(each.dims[0] for each in self.contents)
		adjust_x = min(each.adjust[0] for each in self.contents)
		self.dims = (largest_w, h)
		self.adjust = (adjust_x, 0)
	
	def kern_top(self): return self.contents[0].kern_top()
	def kern_bottom(self): return self.contents[-1].kern_bottom()
	def allow_kern_upward(self): return self.contents[0].allow_kern_upward()
	def allow_kern_downward(self): return self.contents[-1].allow_kern_downward()
	def kern_left(self): return min(c.kern_left() for c in self.contents)
	def kern_right(self): return min(c.kern_right() for c in self.contents)
	def allow_kern_leftward(self): return all(c.allow_kern_leftward() for c in self.contents)
	def allow_kern_rightward(self): return all(c.allow_kern_rightward() for c in self.contents)
	
	def functional_form(self):
		# This is mostly the same as HStack's implementation
		# But with one additional complication
		raw_children = [child.functional_form() for child in self.contents]
		children = []
		for child in raw_children:
			if child is None: continue
			elif isinstance(child, VStack): children.extend(child.contents)
			else: children.append(child)
		if len(children) == 1:
			return children[0]
		if not children:
			return None
		
		# Here's the extra part
		# Sometimes there's an ambiguity where something can be written either as HStacks of VStacks, or as VStacks of HStacks
		# (Consider, for example, the ZA sign)
		# In this case, we need to choose one of the two to be canonical
		# And we chose an HStack of VStacks
		# So if we see a VStack of HStacks, we need to change that
		if all(isinstance(child, HStack) for child in children):
			l = len(children[0].contents)
			if all(len(child.contents)==l for child in children):
				# So now we know that we've got a VStack of HStacks
				# And that all those HStacks are the same size
				# So, time to change that around
				child_contents = [child.contents for child in children]
				new_contents = list(zip(*child_contents))
				new_stacks = [VStack(list(c)) for c in new_contents]
				new_parent = HStack(new_stacks)
				# Then we re-functionalize this in case there are any new nesting issues that need to be handled
				return new_parent.functional_form()
		
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

class Superpose(Container):
	def __init__(self, *args, pulldir=Orientation.NEITHER, **kwargs):
		super().__init__(*args, **kwargs)
		self.pulldir = pulldir # Used in the functional-form calculations to make sure that we don't "pull out" elements in the wrong way
	
	def __str__(self):
		return '(' + ','.join(str(c) for c in self.contents) + ')'
	
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
	
	def functional_form(self):
		raw_children = [child.functional_form() for child in self.contents]
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
	
	def traverse(self):
		yield self
		yield from self.child.traverse()
	
	def functional_form(self):
		# Adjustments are ignored in functional form
		return self.child.functional_form()

class Tenu(Adjustment): # Rotate a container 45 degrees
	def __str__(self):
		return str(self.child) + 'T'
	def can_expand_horizontally(self): return False
	def can_expand_vertically(self): return False
	def propagate_dimensions(self, dims, pos):
		(x,y) = pos
		(w,h) = dims
		d = min(dims)
		self.adjust = (dx,dy) = (w-d)/2, (h-d)/2
		self.pos = (x+dx, y+dy)
		self.dims = (d, d)
		small = d*sqrt(2)/2 # Scale down to fit in a smaller square
		self.child.propagate_dimensions((small, small), (0, 0)) # Set position to (0,0) to make the rendering hack work better
	def draw(self, rend):
		with rend.tenu(self.pos, self.dims): # Context manager that adjusts the coordinate system of the canvas for this one instance, then puts it back afterward
			self.child.draw(rend)

class Expand(Adjustment): # Request twice as much space as usual from our parent
	# This class actually does basically nothing - but it's checked for in the kerning algorithm in VStack and HStack
	# Note that this prevents its child from expanding! It's meant to be used when an element doesn't ask for enough space, and expanding elements always ask for as much space as possible. So don't use this on an expanding element unless you want to give it a fixed size.
	def __str__(self):
		return str(self.child) + 'E'
	def can_expand_horizontally(self): return False
	def can_expand_vertically(self): return False
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
	def __str__(self):
		return str(self.child) + 'M'
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
	def __str__(self): return str(self.child) + 'R'
	def can_expand_horizontally(self): return False
	def can_expand_vertically(self): return False
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

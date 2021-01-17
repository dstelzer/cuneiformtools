from enum import Enum
from math import sqrt

class Modifier(Enum): # Modifiers that can be applied to strokes
	HEADSHORT = "'"
	TAILSHORT = '"'
	DOUBLE = '2'
	TRIPLE = '3'

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
	
	def add_modifier(self, mod): raise ValueError('Only strokes can have modifiers; you probably want an adjustment instead') # Stroke overrides this method

class CanvasShape(Enum):
	PORTRAIT = 'P'
	LANDSCAPE = 'L'
	SQUARE = 'S'
	WIDE = 'W'
	FUNCTIONAL = '_F' # This one isn't represented by a single character so it'll never show up in parsing; it's used to indicate a "functional form" designed to make comparisons easy rather than to look nice

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
		
		self.internal.propagate_dimensions(self.dims, (0, 0))
	
	def draw(self, rend):
		self.internal.draw(rend)
	
	def functional_form(self):
		return Canvas(CanvasShape.FUNCTIONAL, self.internal.functional_form())

class Stroke(Element):
	def __init__(self, mods=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.mods = mods or set()
	
	def modstr(self):
		return ''.join(sorted(m.value for m in self.mods)) # Sort so that it's deterministic
	
	def add_modifier(self, mod):
		self.mods.add(Modifier(mod))
		if Modifier.DOUBLE in self.mods and Modifier.TRIPLE in self.mods:
			raise ValueError('A stroke cannot be both double and triple')
	
	def propagate_dimensions(self, dims, pos):
		self.dims = dims
		self.pos = pos
		self.adjust = 0,0

class Void(Stroke): # An emptiness that takes up space and does nothing else
	def __init__(self, *args, **kwargs):
		super().__init__(mods=None, *args, **kwargs)
	def __str__(self): return '0'
	def can_expand_horizontally(self): return True
	def can_expand_vertically(self): return True
	def draw(self, rend): pass
	def add_modifier(self, mod): raise ValueError('Voids do not support modifiers')
	
	def functional_form(self): return None # Voids are ignored in functional form

class Vertical(Stroke):
	def __str__(self):
		return 'v' + self.modstr()
	
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
		if Modifier.DOUBLE in self.mods: return VStack([Vertical(), Vertical()])
		else: return Vertical()

class Horizontal(Stroke):
	def __str__(self):
		return 'h' + self.modstr()
	
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
		if Modifier.DOUBLE in self.mods: return HStack([Horizontal(), Horizontal()])
		else: return Horizontal()

class UpDiag(Stroke):
	def __str__(self):
		return 'u' + self.modstr()
	
	def can_expand_vertically(self): return True
	def can_expand_horizontally(self): return True
	def orient(self): return Orientation.WIDE # Diagonals "act" wide more than they "act" tall, in my experience
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'b')
		rend.draw_upward(*self.pos, *self.dims, self.mods)
	
	def functional_form(self):
		# There are no diagonal stacks, so we just discard all modifiers
		return UpDiag()

class DownDiag(Stroke):
	def __str__(self):
		return 'd' + self.modstr()
	
	def can_expand_vertically(self): return True
	def can_expand_horizontally(self): return True
	def orient(self): return Orientation.WIDE # Diagonals "act" wide more than they "act" tall, in my experience
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'b')
		rend.draw_downward(*self.pos, *self.dims, self.mods)
	
	def functional_form(self):
		# There are no diagonal stacks, so we just discard all modifiers
		return DownDiag()

class Winkelhaken(Stroke):
	def __init__(self, *args, **kwargs):
		super().__init__(mods=None, *args, **kwargs)
	
	def add_modifier(self, mod): raise ValueError('Winkelhaken do not support modifiers')
	
	def __str__(self):
		return 'c'
	
	def propagate_dimensions(self, dims, pos):
		(w,h) = dims
		adj_x, adj_y = 0, 0
		new_w = min(w, h/2)
		new_h = min(h, 2*w)
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
		rend.draw_hook(*self.pos, *self.dims)
	
	def functional_form(self): return Winkelhaken() # No mods to worry about

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
	
	# TODO: This is good for NI, but gives possibly-not-desirable results for TA. Is that okay? Test it and make sure.
	def clean_intersections(self): # Pull intersecting elements out as far as possible, to deal with the ambiguities in superpositioning
		# Are all our non-superposed children pointed the same way?
		overall = Orientation.consensus(child.orient() for child in self.contents if not isinstance(child, Superpose))
		if overall == Orientation.NEITHER or overall == Orientation.MIXED: return self # Don't do this if there's no clear orientation
		def conflicts(o): return o != overall and o != Orientation.MIXED
		
		outer_elements = []
		for i, child in enumerate(self.contents):
			if isinstance(child, Superpose):
				good = [e for e in child.contents if not conflicts(e.orient())]
				bad = [e for e in child.contents if conflicts(e.orient())]
				if bad: # We need to make a change
					self.contents[i] = Superpose(good)
					outer_elements.extend(bad)
		
		if not outer_elements: return self # No changes necessary
		# Otherwise, though, we need to put these "pulled-out" elements in superposition with the whole container
		outer_elements.append(self)
		return Superpose(outer_elements).functional_form() # Gotta do the functional cleanup all over again just in case

class HStack(Container):
	def __str__(self):
		return '[' + ','.join(str(c) for c in self.contents) + ']'
	
	def propagate_dimensions(self, dims, pos):
		self.dims = (w,h) = dims
		self.pos = (x,y) = pos
		self.adjust = 0,0
		pieces = len(self.contents)
		each_w = w/pieces
		for i, each in enumerate(self.contents): each.propagate_dimensions((each_w, h), (x+i*each_w, y))
		
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
			current_position = 0
			for i, each in enumerate(self.contents):
				left_kerning = self.contents[i-1].kern_right() if i-1>=0 else 0
				right_kerning = self.contents[i+1].kern_left() if i+1<len(self.contents) else 0
				previous_position = current_position
				current_position -= each.adjust[0] # If the element adjusted its own position, we need to take that into account when assigning its new coordinates
				
				if each.can_expand_horizontally(): # This is a flexible one
					new_w = portion + left_kerning + right_kerning # The new width to assign
					new_x = current_position - left_kerning
					each.propagate_dimensions((new_w, h), (new_x, y))
					current_position += portion
					# current_position += each.adjust[0] # Flexible ones should never have adjustment values in the direction that they're flexible - they're expected to take up all the space they're given
				
				elif left_kerning and each.allow_kern_leftward(): # This one should be nudged to the left
					new_x = current_position - left_kerning
					each.propagate_dimensions((each_w, h), (new_x, y))
					# I'm not exactly sure why, but propagating the dimensions with the original width and height, and then applying the adjustment values, works better than propagating with the width and height stored in each.dims. So propagate(each.dims, (new_x, each.pos[1])) doesn't work, and this does.
					current_position += each.dims[0] - left_kerning
					current_position += each.adjust[0]
				
				else: # This one needs no special handling
					new_x = current_position
					each.propagate_dimensions((each_w, h), (new_x, y))
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

class VStack(Container):
	def __str__(self):
		return '{' + ','.join(str(c) for c in self.contents) + '}'
	
	def propagate_dimensions(self, dims, pos):
		self.dims = (w,h) = dims
		self.pos = (x,y) = pos
		self.adjust = 0,0
		pieces = len(self.contents)
		each_h = h/pieces
		for i, each in enumerate(self.contents): each.propagate_dimensions((w, each_h), (x, y+i*each_h))
		
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
			current_position = 0
			for i, each in enumerate(self.contents):
				top_kerning = self.contents[i-1].kern_bottom() if i-1>=0 else 0
				bottom_kerning = self.contents[i+1].kern_top() if i+1<len(self.contents) else 0
				previous_position = current_position
				current_position -= each.adjust[1] # If the element adjusted its own position, we need to take that into account when assigning its new coordinates
				
				if each.can_expand_vertically(): # This is a flexible one
					new_h = portion + top_kerning + bottom_kerning # The new height to assign
					new_y = current_position - top_kerning
					each.propagate_dimensions((w, new_h), (x, new_y))
					current_position += portion
					# See HStack for justification
				
				elif top_kerning and each.allow_kern_upward(): # This one should be nudged upward
					new_y = current_position - top_kerning
					each.propagate_dimensions((w, each_h), (x, new_y))
					# As above
					current_position += each.dims[1] - top_kerning
					current_position += each.adjust[1]
				
				else: # This one needs no special handling
					new_y = current_position
					each.propagate_dimensions((w, each_h), (x, new_y))
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

class Superpose(Container):
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
		children = [child.functional_form() for child in self.contents]
		children = [child for child in children if child is not None] # Remove None elements (TODO filter)
		if len(children) == 1: return children[0]
		if not children: return None
		children.sort(key=str) # Sort by ASCII form - it's arbitrary but consistent
		return Superpose(children)

class Adjustment(Container):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if len(self.contents) != 1: raise ValueError('Adjustments must contain a single element')
		self.child = self.contents[0]
	
	def functional_form(self):
		# Adjustments are ignored in functional form
		return self.child.functional_form()

class Tenu(Adjustment): # Rotate a container 45 degrees
	def __str__(self):
		return f'<T {self.child}>'
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

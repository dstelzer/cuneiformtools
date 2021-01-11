from enum import Enum
from math import sqrt

class Modifier(Enum): # Modifiers that can be applied to strokes
	HEADSHORT = "'"
	TAILSHORT = '"'
	DOUBLE = '2'
	TRIPLE = '3' # TODO
	# TODO incorporate doubling here?

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
	
	def add_modifier(self, mod): raise ValueError('Only strokes can have modifiers; you probably want an adjustment instead')

class CanvasShape(Enum):
	PORTRAIT = 'P'
	LANDSCAPE = 'L'
	SQUARE = 'S'
	WIDE = 'W'

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
		
		self.internal.propagate_dimensions(self.dims, (0, 0))
	
	def draw(self, rend):
		self.internal.draw(rend)

class Stroke(Element):
	def __init__(self, mods=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.mods = mods or set()
	
	def modstr(self):
		return ''.join(m.value for m in self.mods)
	def add_modifier(self, mod):
		self.mods.add(Modifier(mod))
	
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
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'b')
		rend.box(self.pos[0]-self.adjust[0], self.pos[1], self.adjust[0], self.dims[1], 'r')
		rend.draw_vertical(*self.pos, *self.dims, self.mods)

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
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'b')
		rend.box(self.pos[0], self.pos[1]-self.adjust[1], self.dims[0], self.adjust[1], 'r')
		rend.draw_horizontal(*self.pos, *self.dims, self.mods)

class UpDiag(Stroke):
	def __str__(self):
		return 'u' + self.modstr()
	
	def can_expand_vertically(self): return True
	def can_expand_horizontally(self): return True
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'b')
		rend.draw_upward(*self.pos, *self.dims, self.mods)

class DownDiag(Stroke):
	def __str__(self):
		return 'd' + self.modstr()
	
	def can_expand_vertically(self): return True
	def can_expand_horizontally(self): return True
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'b')
		rend.draw_downward(*self.pos, *self.dims, self.mods)

class Winkelhaken(Stroke):
	def __init__(self, *args, **kwargs):
		super().__init__(mods=None, *args, **kwargs)
	
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

class Container(Element):	
	def __init__(self, contents=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if contents is None: contents = []
		self.contents = contents
	
	def can_expand_horizontally(self): return any(e.can_expand_horizontally() for e in self.contents)
	def can_expand_vertically(self): return any(e.can_expand_vertically() for e in self.contents)
	
	def draw(self, rend):
		rend.box(*self.pos, *self.dims, 'g')
		for each in self.contents: each.draw(rend)

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

class Adjustment(Container):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if len(self.contents) != 1: raise ValueError('Adjustments must contain a single element')
		self.child = self.contents[0]

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

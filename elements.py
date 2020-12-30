

from enum import Enum

class Element:
	def can_expand_horizontally(self): return False
	def can_expand_vertically(self): return False
	def kern_left(self): return 0
	def kern_right(self): return 0
	def kern_top(self): return 0
	def kern_bottom(self): return 0

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
		if isinstance(self.internal, Number): raise ValueError('Canvas cannot contain numbers directly')
	
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
		# TODO sizing
		self.internal.draw(rend)

class Number(Element):
	def __init__(self, value, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.value = int(value)
		if self.value < 1 or self.value > 9: raise ValueError('Number must be a single digit', self.value)
	
	def __str__(self):
		return str(self.value)

class Stroke(Element):
	def __init__(self, doubled, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.doubled = doubled
	
	def propagate_dimensions(self, dims, pos):
		self.dims = dims
		self.pos = pos

class Vertical(Stroke):
	def __str__(self):
		return 'V' if self.doubled else 'v'
	
	def can_expand_vertically(self): return True
	def propagate_dimensions(self, dims, pos):
		(w,h) = dims
		act = min(w, MAXIMUM_HEAD_SIZE)
		self.dims = (act, h)
		(x,y) = pos
		if w > act: x += (w-act)/2
		self.pos = (x,y)
	def kern_left(self): return self.dims[0]/2
	def kern_right(self): return self.dims[0]/2
	
	def draw(self, rend):
		if self.doubled: rend.draw_double(*self.pos, *self.dims)
		else: rend.draw_vertical(*self.pos, *self.dims)

class Horizontal(Stroke):
	def __str__(self):
		return 'H' if self.doubled else 'h'
	
	def can_expand_horizontally(self): return True
	def propagate_dimensions(self, dims, pos):
		(w,h) = dims
		act = min(h, MAXIMUM_HEAD_SIZE)
		self.dims = (w, act)
		(x,y) = pos
		if h > act: y += (h-act)/2
		self.pos = (x,y)
	def kern_top(self): return self.dims[0]/2
	def kern_bottom(self): return self.dims[0]/2
	
	def draw(self, rend):
		if self.doubled: rend.draw_double_horizontal(*self.pos, *self.dims)
		else: rend.draw_horizontal(*self.pos, *self.dims)

class UpDiag(Stroke):
	def __str__(self):
		return 'U' if self.doubled else 'u'
	
	def can_expand_vertically(self): return True
	def can_expand_horizontally(self): return True

class DownDiag(Stroke):
	def __str__(self):
		return 'D' if self.doubled else 'd'
	
	def can_expand_vertically(self): return True
	def can_expand_horizontally(self): return True

class Winkelhaken(Stroke):
	def __init__(self, *args, **kwargs):
		super().__init__(doubled=False, *args, **kwargs)
	
	def __str__(self):
		return 'c'
	
	def propagate_dimensions(self, dims, pos):
		(w,h) = dims
		new_w = min(w, h/2)
		new_h = min(h, 2*w)
		self.dims = (new_w, new_h)
		(x,y) = pos
		if w > new_w: x += (w-new_w)/2
		if h > new_h: y += (h-new_h)/2
		self.pos = (x,y)
	
	def draw(self, rend):
		rend.draw_hook(*self.pos, *self.dims)

class Container(Element):
	only_repeat_strokes = True # Inherited by every child except Nudge
	
	def __init__(self, contents=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if contents is None: contents = []
		self.contents = contents
		self.number = None
		
		number_count = sum(1 for e in self.contents if isinstance(e, Number))
		if number_count > 1: raise ValueError('Only one number allowed')
		if number_count == 1:
			if len(self.contents) != 2: raise ValueError('A number must be followed by a single element')
			if not isinstance(self.contents[0], Number): raise ValueError('The number must come first')
			if self.only_repeat_strokes and not isinstance(self.contents[1], Stroke): raise ValueError('Only single strokes can be repeated')
			self.number = self.contents[0]
			self.contents = self.contents[1:]
	
	def can_expand_horizontally(self): return any(e.can_expand_horizontally() for e in self.contents)
	def can_expand_vertically(self): return any(e.can_expand_vertically() for e in self.contents)
	
	def draw(self, rend):
		for each in self.contents: each.draw(rend)

class HStack(Container):
	def __str__(self):
		if self.number is not None: return f'[{self.number} {self.contents[0]}]'
		else: return '[' + ','.join(str(c) for c in self.contents) + ']'
	
	def propagate_dimensions(self, dims, pos):
		self.dims = (w,h) = dims
		self.pos = (x,y) = pos
		pieces = self.number or len(self.contents)
		each_w = w/pieces
		for i, each in enumerate(self.contents): each.propagate_dimensions((each_w, h), (x+i*each_w, y))
		
		# Now check if we have to do any fancy kerning and recalculation
		if (not self.number) and any(each.can_expand_horizontally() for each in self.contents):
			# In this case, we have different types of strokes together, and some of them can expand horizontally
			# So first we calculate how much space is currently used and can't be avoided
			fixed_space = 0
			for i, each in enumerate(self.contents):
				if each.can_expand_horizontally(): continue # Ignore flexible ones
				used = each.dims[0]
				# Can we kern this into its neighbors?
				if i-1 >= 0 and not each.kern_left():
					used -= self.contents[i-1].kern_right()
				if i+1 < len(self.contents) and not each.kern_right():
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
				
				if each.can_expand_horizontally(): # This is a flexible one
					new_w = portion + left_kerning + right_kerning # The new width to assign
					new_x = current_position - left_kerning
					each.propagate_dimensions((new_w, h), (new_x, y))
					current_position += portion
				
				elif left_kerning and not each.kern_left(): # This one should be nudged to the left
					new_x = current_position - left_kerning
					each.propagate_dimensions((each_w, h), (new_x, y))
					current_position += each.dims[0] - left_kerning
				
				else: # This one needs no special handling
					new_x = current_position
					each.propagate_dimensions((each_w, h), (new_x, y))
					current_position += each.dims[0]
				
				if right_kerning and not each.kern_right() and not each.can_expand_horizontally(): # Finally, check to see if we need to adjust the kerning for the *next* element
					current_position -= right_kerning
		#			print('Applying right kerning', previous_position, right_kerning, current_position)
				if previous_position > current_position: # But don't allow any element to take less than zero width
					current_position = previous_position
	
	def kern_left(self): return self.contents[0].kern_left()
	def kern_right(self): return self.contents[-1].kern_right()

class VStack(Container):
	def __str__(self):
		if self.number is not None: return '{' + f'{self.number} {self.contents[0]}' + '}'
		else: return '{' + ','.join(str(c) for c in self.contents) + '}'
	
	def propagate_dimensions(self, dims, pos):
		self.dims = (w,h) = dims
		self.pos = (x,y) = pos
		pieces = self.number or len(self.contents)
		each_h = h/pieces
		for i, each in enumerate(self.contents): each.propagate_dimensions((w, each_h), (x, y+i*each_h))
		
		# Now check if we have to do any fancy kerning and recalculation
		if (not self.number) and any(each.can_expand_vertically() for each in self.contents):
			# In this case, we have different types of strokes together, and some of them can expand vertically
			# So first we calculate how much space is currently used and can't be avoided
			fixed_space = 0
			for i, each in enumerate(self.contents):
				if each.can_expand_vertically(): continue # Ignore flexible ones
				used = each.dims[1]
				# Can we kern this into its neighbors?
				if i-1 >= 0 and not each.kern_top():
					used -= self.contents[i-1].kern_bottom()
				if i+1 < len(self.contents) and not each.kern_bottom():
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
				
				if each.can_expand_vertically(): # This is a flexible one
					new_h = portion + top_kerning + bottom_kerning # The new height to assign
					new_y = current_position - top_kerning
					each.propagate_dimensions((w, new_h), (x, new_y))
					current_position += portion
				
				elif top_kerning and not each.kern_top(): # This one should be nudged upward
					new_y = current_position - top_kerning
					each.propagate_dimensions((w, each_h), (x, new_y))
					current_position += each.dims[1] - top_kerning
				
				else: # This one needs no special handling
					new_y = current_position
					each.propagate_dimensions((w, each_h), (x, new_y))
					current_position += each.dims[1]
				
				if bottom_kerning and not each.kern_bottom() and not each.can_expand_vertically(): # Finally, check to see if we need to adjust the kerning for the *next* element
					current_position -= bottom_kerning
				if previous_position > current_position: # But don't allow any element to take less than zero height
					current_position = previous_position
	
	def kern_top(self): return self.contents[0].kern_top()
	def kern_bottom(self): return self.contents[-1].kern_bottom()

class Superpose(Container):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if self.number is not None: raise ValueError('Superposition does not allow repetition')
	
	def __str__(self):
		return '(' + ','.join(str(c) for c in self.contents) + ')'
	
	def propagate_dimensions(self, dims, pos):
		self.dims = dims
		self.pos = pos
		for child in self.contents: child.propagate_dimensions(dims, pos)
	
	def kern_left(self): return min(c.kern_left() for c in self.contents)
	def kern_right(self): return min(c.kern_right() for c in self.contents)
	def kern_top(self): return min(c.kern_top() for c in self.contents)
	def kern_bottom(self): return min(c.kern_bottom() for c in self.contents)

class Nudge(Container):
	only_repeat_strokes = False
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if len(self.contents) > 1: raise ValueError('<>-containers can contain only a single element')
		if self.number is None: self.number = Number(5) # Centered
		self.region = self.number
		self.child = self.contents[0]
	
	def __str__(self):
		return f'<{self.region} {self.child}>'
	
	def can_expand_horizontally(self): return False
	def can_expand_vertically(self): return False
	def propagate_dimensions(self, dims, pos):
		self.dims = (w,h) = dims
		self.pos = (x,y) = pos
		w, h = w/3, h/3 # 1/9 of the total area
		which_x = self.region.value % 3 # Choose a region
		which_y = self.region.value // 3 # (Each coord in [0,3])
		x += which_x * w
		y += which_y * h
		self.child.propagate_dimensions((w,h), (x,y))

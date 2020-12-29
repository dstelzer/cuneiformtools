

from enum import Enum

class Element:
	def can_expand_horizontally(self): return False
	def can_expand_vertically(self): return False

class CanvasShape(Enum):
	PORTRAIT = 'P'
	LANDSCAPE = 'L'
	SQUARE = 'S'

class Canvas(Element):
	def __init__(self, shape, internal, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.shape = CanvasShape(shape)
		self.internal = internal
		if isinstance(self.internal, Number): raise ValueError('Canvas cannot contain numbers directly')
	
	def __str__(self):
		return f'{self.shape.value} {self.internal}'
	
	def propagate_dimensions(self, _=None):
		if self.shape == CanvasShape.SQUARE: self.dims = (3, 3)
		elif self.shape == CanvasShape.PORTRAIT: self.dims = (2, 3)
		elif self.shape == CanvasShape.LANDSCAPE: self.dims = (3, 2)
		
		self.internal.propagate_dimensions(self.dims)

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
	
	def propagate_dimensions(self, dims):
		self.dims = self.actual_dims = dims

class Vertical(Stroke):
	def __str__(self):
		return 'V' if self.doubled else 'v'
	
	def can_expand_vertically(self): return True
	def propagate_dimensions(self, dims):
		self.dims = (w,h) = dims
		actual_width = min(h/2, w/2) # Allow other elements to extend into our space in order to touch the center of the stroke
		self.actual_dims = actual_width, h
	
	def draw(self, context, center):
		cx, cy = center
		w, h = self.dims
		if h < w: h = w
		
		nw = (cx-w/2, cy-h/2)
		ne = (cx+w/2, cy-h/2)
		pivot = (cx+w/2, cy-h/2+w/2)
		r = w/2
		join = (cx, cy-h/2+w)
		s = (cx, cy+h/2)
		
		context.move_to(*nw)
		context.line_to(*ne)
		context.arc_negative(*pivot, r, pi/2, pi)
		context.line_to(*s)
		context.stroke()

class Horizontal(Stroke):
	def __str__(self):
		return 'H' if self.doubled else 'h'
	
	def can_expand_horizontally(self): return True
	def propagate_dimensions(self, dims):
		self.dims = (w,h) = dims
		actual_height = min(w/2, h/2)
		self.actual_dims = w, actual_height

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
	
	def propagate_dimensions(self, dims):
		self.dims = (w,h) = dims
		act = min(w, h)
		self.actual_dims = act, act

class Container(Element):
	only_repeat_strokes = True # Inherited by every child except nudge
	
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

class HStack(Container):
	def __str__(self):
		if self.number is not None: return f'[{self.number} {self.contents[0]}]'
		else: return '[' + ','.join(str(c) for c in self.contents) + ']'
	
	def propagate_dimensions(self, dims):
		self.dims = self.actual_dims = (w,h) = dims
		pieces = self.number or len(self.contents)
		each_w = w/pieces
		for each in self.contents: each.propagate_dimensions((each_w, h))
		
		if not self.number: # This container has a mixture of types in it
			# So we can check if any of those aren't using their full width, and if not, reallocate that width to the ones that *can* use it
			# (We assume that elements that can expand horizontally will always use their full space, and elements that can't, may not)
			fixed = sum(each.actual_dims[0] for each in self.contents if not each.can_expand_horizontally())
			count = sum(1 for each in self.contents if each.can_expand_horizontally())
			each_w = (w - fixed) / count
			for each in self.contents:
				if each.can_expand_horizontally():
					each.propagate_dimensions((each_w, h))

class VStack(Container):
	def __str__(self):
		if self.number is not None: return '{' + f'{self.number} {self.contents[0]}' + '}'
		else: return '{' + ','.join(str(c) for c in self.contents) + '}'
	
	def propagate_dimensions(self, dims):
		self.dims = self.actual_dims = (w,h) = dims
		pieces = self.number or len(self.contents)
		each_h = h/pieces
		for each in self.contents: each.propagate_dimensions((w, each_h))
		
		if not self.number: # See HStack for explanation
			fixed = sum(each.actual_dims[1] for each in self.contents if not each.can_expand_vertically())
			count = sum(1 for each in self.contents if each.can_expand_vertically())
			each_h = (h - fixed) / count
			for each in self.contents:
				if each.can_expand_vertically():
					each.propagate_dimensions((w, each_h))

class Superpose(Container):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if self.number is not None: raise ValueError('Superposition does not allow repetition')
	
	def __str__(self):
		return '(' + ','.join(str(c) for c in self.contents) + ')'
	
	def propagate_dimensions(self, dims):
		self.dims = self.actual_dims = dims
		for child in self.contents: child.propagate_dimensions(dims)

class Nudge(Container):
	only_repeat_strokes = False
	
	def __init__(self, *args, **kwargs):
		super().__init__(self, *args, **kwargs)
		if len(self.contents) > 1: raise ValueError('<>-containers can contain only a single element')
		if self.number is None: self.number = 5 # Centered
		self.position = self.number
		self.child = self.contents[0]
	
	def __str__(self):
		return f'<{self.position} {self.child}>'
	
	def can_expand_horizontally(self): return False
	def can_expand_vertically(self): return False
	def propagate_dimensions(self, dims):
		self.dims = self.actual_dims = (w,h) = dims
		w, h = w/3, h/3 # 1/9 of the area
		self.child.propagate_dimensions((w,h))

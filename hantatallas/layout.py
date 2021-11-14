from enum import Enum

try:
	from elements import Element
except ImportError:
	from .elements import Element

class Justification(Enum):
	LEFT = 'l'
	RIGHT = 'r'
	CENTER = 'c'
	WORD = 'w'
	SIGN = 's'

class Spacer:
	dims = (1, 1)
	def draw(self, rend): pass
	def propagate_dimensions(self, unused1=None, unused2=None): pass # These two functions should never be called but are provided just in case

class Fill:
	dims = (1, 1)
	def __init__(self, damaged=False): self.damaged = damaged
	def draw(self, rend): pass # Even if damaged, this is handled specifically in the layout engine, not delegated here (if this ever even gets called)
	def propagate_dimensions(self, unused1=None, unused2=None): pass

class Ruling: pass

class Layout:
	def __init__(self, renderclass, justify=Justification.LEFT, size=256, margin=1/8, leading=1/4, spacing=1/2, kerning=1/8, absolute=False, fixed=0):
		self.renderclass = renderclass
		self.justify = Justification(justify)
		divisor = size if absolute else 1
		self.size = size
		self.margin = margin / divisor
		self.size = size / divisor
		self.leading = leading / divisor
		self.spacing = spacing / divisor
		self.kerning = kerning / divisor
		self.fixed = fixed / divisor
		self.ready = False # Do we have a renderer ready to go? No we do not
	
	@staticmethod
	def should_kern_between(first, second):
		# Don't kern if it involves spaces or fills
		return isinstance(first, Element) and isinstance(second, Element)
	
	def row_width(self, row):
		if isinstance(row, Ruling): return 0
		sign_total = sum(sign.dims[0] for sign in row if isinstance(sign, Element)) # Width of each sign
		space_total = sum(self.spacing for space in row if isinstance(space, Spacer) or isinstance(space, Fill)) # Width of each space (treating fills as spaces)
		kern_total = sum(self.kerning for (a,b) in zip(row,row[1:]) if self.should_kern_between(a, b)) # Kerning between every two adjacent signs
		return sign_total + space_total + kern_total
	
	def render(self, rows, **rendparams):
		for row in rows:
			if not isinstance(row, Ruling):
				for sign in row:
					if isinstance(sign, Element):
						sign.propagate_dimensions()
		
		height = sum(1 for row in rows if not isinstance(row, Ruling)) + self.leading*(len(rows)-1) # Rulings have no height but still get leading between them and the next line
		width = max(self.row_width(row) for row in rows)
		
		if self.fixed:
			if width > self.fixed: raise ValueError(f'Fixed width of {self.fixed} is too small for this text; need at least {width}')
			width = self.fixed
		self.line_width = width
		
		full_width = int((width + 2*self.margin) * self.size)
		full_height = int((height + 2*self.margin) * self.size)
		self.rend = self.renderclass(full_width, full_height, skip=True, **rendparams)
		self.rend.ctx.set_source_rgba(*self.rend.bgcolor)
		self.rend.ctx.rectangle(0, 0, full_width, full_height) # Manual blanking
		self.rend.ctx.fill()
		
		self.rend.ctx.save()
		self.rend.ctx.scale(self.size, self.size)
		self.rend.ctx.translate(self.margin, self.margin)
		self.ready = True
		
		y = 0
		for row in rows:
			if isinstance(row, Ruling):
				self.render_rule(y)
			else:
				self.render_row(row, y)
				y += 1
			y += self.leading
		
		self.rend.ctx.restore()
		
		return self.rend
	
	def render_rule(self, y): # TODO should this be delegated to the renderer?
		self.rend.begin_drawing()
		self.rend.ctx.move_to(0, y)
		self.rend.ctx.line_to(self.line_width, y)
		self.rend.ctx.stroke()
	
	def render_row(self, row, y):
		if not self.ready: raise ValueError('Renderer is not ready!') # Don't try to render anything if we don't have a renderer set up
		goal = self.line_width
		actual = self.row_width(row)
		difference = goal - actual
		fills = sum(1 for sign in row if isinstance(sign, Fill))
		
		left_space = 0
		right_space = 0
		spacing = self.spacing
		kerning = self.kerning
		filling = self.spacing # By default, fills are equivalent to spaces
		
		if fills: # If we have any fills, they'll absorb all the difference
			filling += difference / fills
		elif self.justify == Justification.LEFT:
			right_space += difference
		elif self.justify == Justification.RIGHT:
			left_space += difference
		elif self.justify == Justification.CENTER:
			left_space += difference/2
			right_space += difference/2
		elif self.justify == Justification.WORD:
			n_spaces = sum(1 for space in row if isinstance(space, Spacer))
			if n_spaces:
				spacing += difference/n_spaces
			else:
				left_space += difference/2
				right_space += difference/2
		elif self.justify == Justification.SIGN:
			factor = self.spacing / self.kerning # How many kerns to a space?
			n_kerns = sum(factor for space in row if isinstance(space, Spacer)) + sum(1 for (a,b) in zip(row, row[1:]) if self.should_kern_between(a, b))
			if n_kerns:
				kerning += difference / n_kerns
				spacing += (difference / n_kerns) * factor
			else: # No kerns to use; as a last resort, just center the sign in the row
				left_space += difference/2
				right_space += difference/2
		else:
			raise ValueError('Unrecognized justification', self.justify)
		
		x = left_space
		prev = None
		for sign in row:
			if self.should_kern_between(sign, prev): x += kerning
			if isinstance(sign, Element):
				self.rend.render_sign_at(sign, x, y)
				x += sign.dims[0]
			elif isinstance(sign, Spacer):
				x += spacing
			elif isinstance(sign, Fill):
				if sign.damaged: self.rend.hatch(x, y-self.leading, filling, self.size+self.leading)
				x += filling
			else:
				raise ValueError('Unrecognized element', sign)
			prev = sign

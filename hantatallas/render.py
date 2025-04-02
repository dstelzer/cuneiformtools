import subprocess as sp
from math import pi, atan, cos, sqrt
from time import sleep
from contextlib import contextmanager
from io import StringIO, BytesIO
from itertools import takewhile, count

import cairo
from PIL.ImageColor import getrgb

# It's hard to know if we need to import these with relative paths or absolute ones, so we just try both
try:
	from elements import Modifier, HStack, VStack, Horizontal, Vertical, Tenu
	from layout import Spacer
except ImportError:
	from .elements import Modifier, HStack, VStack, Horizontal, Vertical, Tenu
	from .layout import Spacer

DRAW_BOXES = False

def frange(start, stop, step): return takewhile(lambda x: x < stop, (start + i * step for i in count())) # Like range for non-integers. https://stackoverflow.com/a/34114983

def colorparse(color): # Convert a color name into a RGBA tuple
	if color is None: return None # Efficiency
	color = str(color).strip()
	if not color: return None
	if color == '0': return (0, 0, 0, 0) # Special case for transparency, since PIL's helper function doesn't do alpha
	# (If you need something more intricate than this, use a transparent background and an opaque foreground and do the rest in your image processing program of choice)
	try:
		r, g, b = getrgb(color)
	except ValueError: return None
	return (r, g, b, 1)

class Renderer: # A very abstract base class that doesn't do much of anything
	def __init__(self, width, height, margin=0, scale=0):
		self.width = width
		self.height = height
		self.margin = margin
		self.scale = scale
		
		self.fullwidth = int(width + margin*2)
		self.fullheight = int(height + margin*2)
	
	def adjust_tree(self, tree): # Make any necessary adjustments to the tree before drawing. This is the renderer's chance to adjust the size and positions of strokes if necessary.
		return tree
	
	def hatch(self, x, y, w, h, highlight=False): # Draw a hatched pattern over a rectangle - the algorithm is designed so that adjacent or overlapping rectangles will always line up their hatching properly
		raise NotImplementedError()
	
	def box(self, *args, **kwargs):
		pass # Does nothing
	
	def draw_rule(self, y, w):
		raise NotImplementedError()
	
	def save_transforms(self): # Save our current transformation state to return to later
		raise NotImplementedError()
	
	def untransform(self): # Restore to the saved transformation state
		raise NotImplementedError()
	
	def rotate(self, theta): # Transform our current environment by rotating around the origin
		raise NotImplementedError()
	
	def translate(self, x, y): # Transform our current environment by moving with respect to the origin
		raise NotImplementedError()
	
	def rescale(self, xs, ys): # Transform our current environment by rescaling it
		raise NotImplementedError()
	
	def setup_scaling(self): # Do initial scalings and translations to take care of the margin
		if self.scale == 0:
			sw = self.width
			sh = self.height
		else:
			sw = sh = self.scale
		self.translate(self.margin, self.margin)
		self.rescale(sw, sh)
	
	def draw_potential_damage(self, x, y, w, h, mods):
		damage = Modifier.DAMAGE in mods
		highlight = Modifier.HIGHLIGHT in mods
		if damage: self.hatch(x, y, w, h, highlight)
	
	def draw_single(self, x, y, w, h, mods):
		raise NotImplementedError() # To be implemented in derived classes
	
	def draw_double(self, x, y, w, h, mods):
		raise NotImplementedError() # Same
	
	def draw_triple(self, x, y, w, h, mods):
		raise NotImplementedError() # Same
	
	def draw_hook(self, x, y, w, h, mods):
		raise NotImplementedError() # Same
	
	def draw_stroke(self, x, y, w, h, mods): # Delegates to the others after handling some common modifiers
		
		# For horizontals and verticals, cutting off a third of the stroke (at head and/or tail) is a good amount of adjustment.
		# But for diagonals, it's more useful to be able to make them be the same length as other strokes.
		# For example, in (vhud), it would be nice to make them fit into a circle rather than a square.
		# So if we're drawing a diagonal, we cut off 1/sqrt(2) of the length, whether it's in one cut or two.
		if Modifier.INTERNAL_DIAGONAL in mods:
			adj_amount = h * (1-1/sqrt(2))
			if Modifier.HEADSHORT in mods and Modifier.TAILSHORT in mods:
				adj_amount /= 2
		else:
			adj_amount = h/3
		
		if Modifier.HEADSHORT in mods:
			h -= adj_amount
			y += adj_amount
		if Modifier.TAILSHORT in mods:
			h -= adj_amount
		
		if Modifier.DOUBLE in mods: self.draw_double(x, y, w, h, mods)
		elif Modifier.TRIPLE in mods: self.draw_triple(x, y, w, h, mods)
		else: self.draw_single(x, y, w, h, mods)
	
	def draw_void(self, x, y, w, h, mods): # Draw absolutely nothing except potential damage
		self.draw_potential_damage(x, y, w, h, mods)
	
	def draw_wildcard(self, x, y, w, h, mods): # Draw a box with an X in it; this is the same between all the different renderers
		raise NotImplementedError()
	
	def draw_cursor(self, x, y, w, h, mods): # As above, this places a cursor (a line or X)
		raise NotImplementedError()
	
	def draw_hook_wrapper(self, x, y, w, h, mods=()):
		self.draw_potential_damage(x, y, w, h, mods)
		self.draw_hook(x, y, w, h, mods)
	
	def draw_vertical(self, x, y, w, h, mods=()):
		self.draw_potential_damage(x, y, w, h, mods)
		self.draw_stroke(x, y, w, h, mods)
	
	def draw_horizontal(self, x, y, w, h, mods=()):
		self.draw_potential_damage(x, y, w, h, mods)
		self.save_transforms()
		self.rotate(-pi/2)
		self.draw_stroke(-y-h, x, h, w, mods)
		self.untransform()
	
	def draw_downward(self, x, y, w, h, mods=()):
		self.draw_potential_damage(x, y, w, h, mods)
		self.save_transforms()
		
#		c = self.ctx
#		c.save()
	#	print(x, y, w, h)
#		c.translate(x, y)
		self.translate(x, y)
		
		theta = atan(h/w)
		phi = (pi/2) - theta
		
		# I need to attach a diagram to make this all make sense...
		head = min(h, 1/3) # The width of the stroke head
		diag = sqrt(w**2 + h**2)
		
	#	if h > w:
	#		x2 = head / (2*cos(phi))
	#		y2 = 0
	#		x3 = -head
	#		cutoff = (head*w) / (2*h)
	#	else:
	#		x2 = 0
	#		y2 = head / (2*cos(theta))
	#		x3 = 0
	#		cutoff = (head*h) / (2*w)
		
		cutoff = 0
		stroke = diag - cutoff
		mods = set(mods) | {Modifier.INTERNAL_DIAGONAL}
		
		#c.translate(x2, y2) # Set the new origin point
	#	c.arc(0, 0, 0.05, 0, pi*2)
#		c.rotate(-phi)
		self.rotate(-phi)
#		c.translate(-head/2, 0)
		self.translate(-head/2, 0)
		#c.translate(x3, 0)
	#	print(head, stroke)
		self.draw_stroke(0, 0, head, stroke, mods)
#		c.restore()
		self.untransform()
	
	def draw_upward(self, x, y, w, h, mods=()):
		self.draw_potential_damage(x, y, w, h, mods)
#		self.ctx.save()
		self.save_transforms()
#		self.ctx.translate(x, y)
		self.translate(x, y)
#		self.ctx.scale(1, -1) # Invert vertical axis
		self.rescale(1, -1)
#		self.ctx.translate(0, -h)
		self.translate(0, -h)
		
		mods = set(mods) | {Modifier.INTERNAL_DIAGONAL} ^ {Modifier.INTERNAL_FLIP} - {Modifier.DAMAGE} # Since we flipped one of the axes we should unflip it for rendering, and since we already drew the damage we shouldn't draw it again. Also this is a diagonal so we mark that here for safety, even though draw_downward should set that again.
		self.draw_downward(0, 0, w, h, mods) # Delegate to downward
		
#		self.ctx.restore()
		self.untransform()
	
	@classmethod
	def render(cls, root, highlight=(), scale=512, *args, **kwargs): # Any additional parameters are passed to the class constructor
		root.propagate_dimensions()
		root.apply_highlighting(highlight)
		rend = cls(int(root.dims[0]*scale), int(root.dims[1]*scale), scale=scale, *args, **kwargs)
		root = rend.adjust_tree(root)
		root.draw(rend)
		return rend
	
	def render_sign_at(self, sign, x, y):
		self.save_transforms()
		self.translate(x, y)
		sign = self.adjust_tree(sign)
		sign.draw(self)
		self.untransform()
	
	@contextmanager
	def tenu(self, pos, dims): # Tilt the whole canvas sideways temporarily
		self.save_transforms()
		
		x, y = pos
		w, h = dims
		
#		c.translate(x, y+h/2)
		self.translate(x, y+h/2)
#		c.rotate(-pi/4)
		self.rotate(-pi/4)
#		c.translate(0, 0)
#		self.translate(0, 0)
		
		yield self # This is where the other rendering happens
		
#		c.restore() # Un-tenu-fy the canvas again
		self.untransform()

class GraphicRenderer(Renderer):
	def __init__(self, width, height, margin=0, scale=0, format='png', bgcolor=None, fgcolor=None, hlcolor=None, strokewidth=None, hatchspace=None, fill=False):
		super().__init__(width, height, margin=margin, scale=scale) # This fills out the basic layout parameters like fullwidth and fullheight
		
		self.format = format
		
		if format == 'svg':
			self.buffer = BytesIO()
			self.surf = cairo.SVGSurface(self.buffer, self.fullwidth, self.fullheight)
		elif format == 'png':
			self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.fullwidth, self.fullheight)
		elif format == 'pdf':
			self.buffer = BytesIO()
			self.surf = cairo.PDFSurface(self.buffer, self.fullwidth, self.fullheight)
		else:
			raise ValueError('Unrecognized format', format)
		
		self.bgcolor = colorparse(bgcolor) or (0.1, 0.1, 0.1, 1)
		self.fgcolor = colorparse(fgcolor) or (1, 1, 1, 1)
		self.hlcolor = colorparse(hlcolor) or (0, 1, 0, 1)
		self.strokewidth = strokewidth or 0.01
		self.fill = fill
		self.hatchspace = hatchspace or 8
		
		self.ctx = cairo.Context(self.surf)
		self.ctx.save() # Save the "base" context: we'll restore to it later every time we need to blank out the canvas
		self.blank(initial=True) # This will call setup_scaling for us afterward
	
	# These four map straightforwardly to Cairo context transforms
	def save_transforms(self):
		self.ctx.save()
	
	def untransform(self):
		self.ctx.restore()
	
	def rotate(self, theta):
		self.ctx.rotate(theta)
	
	def translate(self, x, y):
		self.ctx.translate(x, y)
	
	def rescale(self, xs, ys):
		self.ctx.scale(xs, ys)
	
	def box(self, x, y, w, h, c):
		if not DRAW_BOXES: return
		
		if c == 'r': col = 1,0,0
		elif c == 'g': col = 0,1,0
		elif c == 'b': col = 0,0,1
		elif c == 'c': col = 0,1,1
		elif c == 'm': col = 1,0,1
		elif c == 'y': col = 1,1,0
		elif c == 'w': col = 1,1,1
		# TODO: Is it worth making this use colorparse?
		# Or is that overkill? Now that kerning works reliably I'm not really using boxes at all any more
		
		self.ctx.set_source_rgba(*col, 0.25)
		self.ctx.rectangle(x, y, w, h)
		self.ctx.fill()
	
	def hatch(self, x, y, w, h, highlight=False): # Draw a hatched pattern over a rectangle - the algorithm is designed so that adjacent or overlapping rectangles will always line up their hatching properly
		if w <= 0 or h <= 0: return # Head off weird edge cases like DAMAGE one-dimensional voids or cursors
		
		self.begin_drawing(highlight)
		spacing = self.hatchspace * self.strokewidth
		
		dist = w+h # Half of the way around the rectangle
		def sw(t): # South and west side
			if t < h: return (x, y+t)
			else: return (x+t-h, y+h)
		def ne(t): # North and east side
			if t < w: return (x+t, y)
			else: return (x+w, y+t-w)
		
		adjust = (-x-y) % spacing
		
		for t in frange(adjust, dist, spacing):
			self.ctx.move_to(*sw(t))
			self.ctx.line_to(*ne(t))
		
		self.ctx.stroke()
	
	def draw_rule(self, y, w):
		self.begin_drawing()
		self.ctx.move_to(0, y)
		self.ctx.line_to(w, y)
		self.ctx.stroke()
	
	def blank(self, initial=False):
		if not initial: self.ctx.restore() # During the initial blanking we haven't made any changes that have to be undone
		self.ctx.set_source_rgba(*self.bgcolor)
		self.ctx.rectangle(0, 0, self.fullwidth, self.fullheight)
		self.ctx.fill()
		self.setup_scaling()
	
	def begin_drawing(self, highlight=False):
		if highlight: self.ctx.set_source_rgba(*self.hlcolor)
		else: self.ctx.set_source_rgba(*self.fgcolor)
		self.ctx.set_line_width(self.strokewidth)
	
	def show(self):
		if self.format == 'png':
			fn = 'tmp.png'
			self.surf.write_to_png(fn)
			sp.run(['xdg-open', fn])
		elif self.format == 'svg':
			fn = 'tmp.svg'
			self.surf.finish()
			with open(fn, 'wb') as f:
				f.write(self.buffer.getvalue())
			sp.run(['xdg-open', fn])
		elif self.format == 'pdf':
			fn = 'tmp.pdf'
			self.surf.show_page()
			self.surf.finish()
			with open(fn, 'wb') as f:
				f.write(self.buffer.getvalue())
			sp.run(['xdg-open', fn])
	
	def get_raw_data(self):
		if self.format == 'png':
			out = BytesIO()
			self.surf.write_to_png(out)
			out.seek(0)
			return out
		elif self.format == 'svg':
			self.surf.finish()
			self.buffer.seek(0)
			return self.buffer
		elif self.format == 'pdf':
			self.surf.show_page()
			self.surf.finish()
			self.buffer.seek(0)
			return self.buffer
	
	def draw_wildcard(self, x, y, w, h, mods): # Draw a box with an X in it; this is the same between all the different graphic renderers
		margin = min(w/3, h/3, 0.05)
		x += margin
		y += margin
		w -= 2*margin
		h -= 2*margin
		
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		nw = (0, 0)
		ne = (w, 0)
		se = (w, h)
		sw = (0, h)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*ne)
		c.line_to(*se)
		c.line_to(*sw)
		c.line_to(*nw)
		c.line_to(*ne) # To make the caps look right
		c.move_to(*se)
		c.line_to(*nw)
		c.move_to(*sw)
		c.line_to(*ne)
		c.stroke()
		
		c.restore()
	
	def draw_cursor(self, x, y, w, h, mods): # As above, this places a cursor (a line or X)
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		nw = (0, 0)
		ne = (w, 0)
		se = (w, h)
		sw = (0, h)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*se)
		c.move_to(*ne)
		c.line_to(*sw)
		c.stroke()
		
		c.restore()
	
#	def render_sign_row(self, row, y, offset):
#		x = offset / self.scale
#		scaled_margin = self.margin / self.scale # We've scaled the canvas so that 1 unit = scale pixels, therefore margin pixels = margin/scale units
#		for sign in row:
#			x += scaled_margin
#			self.render_sign_at(sign, x, y)
#			x += sign.dims[0] # Sign width
	
#	def render_sign_rows(self, rows, offsets):
#		y = 0
#		scaled_margin = self.margin / self.scale # See above
#		for row, offset in zip(rows, offsets):
#			y += scaled_margin * 2
#			self.render_sign_row(row, y, offset)
#			y += 1 # Sign height (fixed)
	
#	@classmethod
#	def render_sequence(cls, rows, highlight=(), scale=512, margin=32, justify='c', *args, **kwargs): # As above re additional parameters
#		# This time, `highlight` is the one that's ignored but included in order to make signatures line up
#		row_widths = []
#		for row in rows:
#			for sign in row:
#				sign.propagate_dimensions()
#			# Now measure this row
#			width = (
#				sum(sign.dims[0] for sign in row)*scale # Signs
#				+ margin * (len(row)+1) # Margins
#			)
#			row_widths.append(width)
#		max_width = max(row_widths)
#		height = scale * len(rows) + margin * 2 * (len(rows)+1)
#		
#		rend = cls(int(max_width), int(height), skip=True, *args, **kwargs)
#		rend.scale = scale
#		rend.margin = margin
#		
#		if justify == 'c':
#			offsets = [(max_width-width)/2 for width in row_widths]
#		elif justify == 'r':
#			offsets = [(max_width-width) for width in row_widths]
#		else:
#			offsets = [0 for width in row_widths]
#		
#		# Manual blanking
#		rend.ctx.set_source_rgba(*rend.bgcolor)
#		rend.ctx.rectangle(0, 0, max_width, height)
#		rend.ctx.fill()
#		
#		rend.ctx.save()
#		rend.ctx.scale(scale, scale)
#		rend.render_sign_rows(rows, offsets)
#		rend.ctx.restore()
#		
#		return rend

class OneSidedRenderer(GraphicRenderer):
	def draw_single(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		if Modifier.INTERNAL_FLIP in mods:
			c.scale(-1, 1) # This particular renderer doesn't make horizontally-symmetric strokes so we need to pay attention to the REVERSE modifier
			c.translate(-w, 0) # Fix our origin after flipping
		
		if Modifier.INVERT in mods:
			c.scale(1, -1)
			c.translate(0, -h)
		
		nw = (0, 0)
		ne = (w, 0)
		pivot = (w, w/2)
		r = w/2
		mid = (w/2, w/2)
		s = (w/2, h)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*ne)
		c.arc_negative(*pivot, r, -pi/2, pi)
		c.move_to(*mid)
		c.line_to(*s)
		c.stroke()
		
		c.restore()
	
	def draw_double(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		if Modifier.INTERNAL_FLIP in mods:
			c.scale(-1, 1) # This particular renderer doesn't make horizontally-symmetric strokes so we need to pay attention to the REVERSE modifier
			c.translate(-w, 0) # Fix our origin after flipping
		
		if Modifier.INVERT in mods:
			c.scale(1, -1)
			c.translate(0, -h)
		
		nw = (0, 0)
		ne = (w, 0)
		pivot1 = (w, w/2)
		w_ = (0, w/2)
		e = (w, w/2)
		pivot2 = (w, w)
		r = w/2
		mid = (w/2, w)
		s = (w/2, h)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*ne)
		c.arc_negative(*pivot1, r, -pi/2, pi)
		c.move_to(*w_)
		c.line_to(*e)
		c.arc_negative(*pivot2, r, -pi/2, pi)
		c.move_to(*mid)
		c.line_to(*s)
		c.stroke()
		
		c.restore()
	
	def draw_triple(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		if Modifier.INTERNAL_FLIP in mods:
			c.scale(-1, 1) # This particular renderer doesn't make horizontally-symmetric strokes so we need to pay attention to this special internal modifier
			c.translate(-w, 0) # Fix our origin after flipping
		
		if Modifier.INVERT in mods:
			c.scale(1, -1)
			c.translate(0, -h)
		
		r = w/2
		nw = (0, 0)
		ne = (w, 0)
		pivot1 = (w, r)
		w_ = (0, r)
		e = (w, r)
		pivot2 = (w, 2*r)
		w2 = (0, 2*r)
		e2 = (w, 2*r)
		pivot3 = (w, 3*r)
		mid = (w/2, 3*r)
		s = (w/2, h)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*ne)
		c.arc_negative(*pivot1, r, -pi/2, pi)
		c.move_to(*w_)
		c.line_to(*e)
		c.arc_negative(*pivot2, r, -pi/2, pi)
		c.move_to(*w2)
		c.line_to(*e2)
		c.arc_negative(*pivot3, r, -pi/2, pi)
		c.move_to(*mid)
		c.line_to(*s)
		c.stroke()
		
		c.restore()
	
	def draw_hook(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		ne = (w, 0)
		se = (w, h)
		w = (0, h/2)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*ne)
		c.line_to(*w)
		c.line_to(*se)
		c.stroke()
		
		c.restore()

class TwoSidedRenderer(GraphicRenderer):
	def draw_single(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		if Modifier.INVERT in mods:
			c.scale(1, -1)
			c.translate(0, -h)
		
		nw = (0, 0)
		ne = (w, 0)
		pivot1 = (w, w/2)
		pivot2 = (0, w/2)
		r = w/2
		mid = (w/2, w/2)
		s = (w/2, h)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*ne)
		c.arc_negative(*pivot1, r, -pi/2, pi)
		c.arc_negative(*pivot2, r, 0, -pi/2)
		if self.fill: c.fill_preserve()
		c.move_to(*mid)
		c.line_to(*s)
		c.stroke()
		
		c.restore()
	
	def draw_double(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		if Modifier.INVERT in mods:
			c.scale(1, -1)
			c.translate(0, -h)
		
		nw = (0, 0)
		ne = (w, 0)
		pivot1r = (w, w/2)
		pivot1l = (0, w/2)
		w_ = (0, w/2)
		e = (w, w/2)
		pivot2r = (w, w)
		pivot2l = (0, w)
		r = w/2
		mid = (w/2, w)
		s = (w/2, h)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*ne)
		c.arc_negative(*pivot1r, r, -pi/2, pi)
		c.arc_negative(*pivot1l, r, 0, -pi/2)
		if self.fill: c.fill_preserve()
		c.move_to(*w_)
		c.line_to(*e)
		c.arc_negative(*pivot2r, r, -pi/2, pi)
		c.arc_negative(*pivot2l, r, 0, -pi/2)
		if self.fill: c.fill_preserve()
		c.move_to(*mid)
		c.line_to(*s)
		c.stroke()
		
		c.restore()
	
	def draw_triple(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		if Modifier.INVERT in mods:
			c.scale(1, -1)
			c.translate(0, -h)
		
		r = w/2
		nw = (0, 0)
		ne = (w, 0)
		pivot1r = (w, r)
		pivot1l = (0, r)
		w_ = (0, r)
		e = (w, r)
		pivot2r = (w, 2*r)
		pivot2l = (0, 2*r)
		w2 = (0, 2*r)
		e2 = (w, 2*r)
		pivot3r = (w, 3*r)
		pivot3l = (0, 3*r)
		mid = (w/2, 3*r)
		s = (w/2, h)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*ne)
		c.arc_negative(*pivot1r, r, -pi/2, pi)
		c.arc_negative(*pivot1l, r, 0, -pi/2)
		if self.fill: c.fill_preserve()
		c.move_to(*w_)
		c.line_to(*e)
		c.arc_negative(*pivot2r, r, -pi/2, pi)
		c.arc_negative(*pivot2l, r, 0, -pi/2)
		if self.fill: c.fill_preserve()
		c.move_to(*w2)
		c.line_to(*e2)
		c.arc_negative(*pivot3r, r, -pi/2, pi)
		c.arc_negative(*pivot3l, r, 0, -pi/2)
		if self.fill: c.fill_preserve()
		c.move_to(*mid)
		c.line_to(*s)
		c.stroke()
		
		c.restore()
	
	def draw_hook(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		ne = (w, 0)
		se = (w, h)
		w = (0, h/2)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*ne)
		c.line_to(*w)
		c.line_to(*se)
		c.curve_to(*se, *w, *ne)
		if self.fill: c.fill_preserve()
		c.stroke()
		
		c.restore()

class TriangleRenderer(GraphicRenderer):
	def draw_single(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		if Modifier.INVERT in mods:
			c.scale(1, -1)
			c.translate(0, -h)
		
		nw = (0, 0)
		ne = (w, 0)
		mid = (w/2, w/2)
		s = (w/2, h)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*ne)
		c.line_to(*mid)
		c.close_path()
		if self.fill: c.fill_preserve()
		c.move_to(*mid)
		c.line_to(*s)
		c.stroke()
		
		c.restore()
	
	def draw_double(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		if Modifier.INVERT in mods:
			c.scale(1, -1)
			c.translate(0, -h)
		
		nw = (0, 0)
		ne = (w, 0)
		mid1 = (w/2, w/2)
		w_ = (0, w/2)
		e = (w, w/2)
		mid2 = (w/2, w)
		s = (w/2, h)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*ne)
		c.line_to(*mid1)
		c.close_path()
		if self.fill: c.fill_preserve()
		c.move_to(*w_)
		c.line_to(*e)
		c.line_to(*mid2)
		c.close_path()
		if self.fill: c.fill_preserve()
		c.move_to(*mid2)
		c.line_to(*s)
		c.stroke()
		
		c.restore()
	
	def draw_triple(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		if Modifier.INVERT in mods:
			c.scale(1, -1)
			c.translate(0, -h)
		
		r = w/2
		nw = (0, 0)
		ne = (w, 0)
		mid1 = (w/2, r)
		w_ = (0, r)
		e = (w, r)
		mid2 = (w/2, 2*r)
		w2 = (0, 2*r)
		e2 = (w, 2*r)
		mid3 = (w/2, 3*r)
		s = (w/2, h)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*ne)
		c.line_to(*mid1)
		c.close_path()
		if self.fill: c.fill_preserve()
		c.move_to(*w_)
		c.line_to(*e)
		c.line_to(*mid2)
		c.close_path()
		if self.fill: c.fill_preserve()
		c.move_to(*w2)
		c.line_to(*e2)
		c.line_to(*mid3)
		c.close_path()
		if self.fill: c.fill_preserve()
		c.move_to(*mid3)
		c.line_to(*s)
		c.stroke()
		
		c.restore()
	
	def draw_hook(self, x, y, w, h, mods):
		if h > 2*w:
			y += (h-2*w)/2
			h = 2*w
		elif w > h/2:
			x += (w-h/2)/2
			w = h/2
		
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		ne = (w, 0)
		se = (w, h)
		w = (0, h/2)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*ne)
		c.line_to(*w)
		c.line_to(*se)
		c.close_path()
		if self.fill: c.fill_preserve()
		c.stroke()
		
		c.restore()

class LinearRenderer(GraphicRenderer):
	WIDTH = 0.1 # The maximum width of a stroke
	SHARPNESS = 0.01 # How much to extend a stroke past the boundaries, to make convergences look good
	
	def draw_single(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		if Modifier.INVERT in mods:
			c.scale(1, -1)
			c.translate(0, -h)
		
		m = w/2 # Midpoint
		nw = (m-self.WIDTH/2, 0)
		ne = (m+self.WIDTH/2, 0)
		s = (m, h+0.01)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*ne)
		c.line_to(*s)
		c.line_to(*nw)
		c.fill()
		
		c.restore()
	
	def draw_double(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		if Modifier.INVERT in mods:
			c.scale(1, -1)
			c.translate(0, -h)
		
		m = w/2 # Midpoint
		nw = (m-self.WIDTH/2, 0)
		ne = (m+self.WIDTH/2, 0)
		_c = (m, h*0.25)
		_w = (m-self.WIDTH/2, h*0.25)
		_e = (m+self.WIDTH/2, h*0.25)
		s = (m, h+0.01)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*ne)
		c.line_to(*_c)
		c.line_to(*_e)
		c.line_to(*s)
		c.line_to(*_w)
		c.line_to(*_c)
		c.line_to(*nw)
		c.fill()
		
		c.restore()
	
	def draw_triple(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		if Modifier.INVERT in mods:
			c.scale(1, -1)
			c.translate(0, -h)
		
		m = w/2 # Midpoint
		nw = (m-self.WIDTH/2, 0)
		ne = (m+self.WIDTH/2, 0)
		_c = (m, h*0.2)
		_w = (m-self.WIDTH/2, h*0.2)
		_e = (m+self.WIDTH/2, h*0.2)
		c2 = (m, h*0.4)
		w2 = (m-self.WIDTH/2, h*0.4)
		e2 = (m+self.WIDTH/2, h*0.4)
		s = (m, h+0.01)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*nw)
		c.line_to(*ne)
		c.line_to(*_c)
		c.line_to(*_e)
		c.line_to(*c2)
		c.line_to(*e2)
		c.line_to(*s)
		c.line_to(*w2)
		c.line_to(*c2)
		c.line_to(*_w)
		c.line_to(*_c)
		c.line_to(*nw)
		c.fill()
		
		c.restore()
	
	def draw_hook(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		ne = (w, 0)
		se = (w, h)
		_w = (0, h/2)
		_c = (self.WIDTH, h/2)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*ne)
		c.line_to(*_c)
		c.line_to(*se)
		c.line_to(*_w)
		c.line_to(*ne)
		c.fill()
		
		c.restore()
	
	'''
	def draw_downward(self, x, y, w, h, mods=()): # We override this method too, because with the linear renderer we can get closer to the corners without the head getting in the way
		self.draw_potential_damage(x, y, w, h, mods)
		# draw_upward by default delegates to this one so we don't need to override it too
		c = self.ctx
		c.save()
		c.translate(x, y)
		theta = pi/2 - atan(h/w)
		c.rotate(-theta)
		c.translate(-self.WIDTH/2, 0)
		hyp = sqrt(w**2+h**2)
		self.draw_stroke(0, 0, self.WIDTH, hyp, mods)
		c.restore()
	'''

class InkRenderer(GraphicRenderer):
	HEAD_SEPARATION = 1/3 # The maximum distance multiple heads can be separated by
	COLLISION_TRIM = 1/12 # The maximum distance we'll shorten a stroke by if its head runs into another stroke - see adjust_tree
	OVERLAP_EPSILON = 1/32 # How close one stroke's head can be to another's body before the algorithm makes it headless
	HEADTAIL_EPSILON = 1/12 # How close the tail of one stroke can be to the head of another before the algorithm separates them for clarity
	
	class MultiStroke: # Represents a block of strokes that should be drawn as one by this renderer; we don't inherit from Element or Stroke directly because we don't actually need all that machinery (the elements.py code has already done all the layout), we just need to keep track of where the stack is and what modifiers it has
		def __init__(self, x, y, w, h, n, mods):
			self.x = x
			self.y = y
			self.w = w
			self.h = h
			self.n = n
			self.mods = mods
		def heads(self):
			if Modifier.DOUBLE in self.mods:
				return 2
			elif Modifier.TRIPLE in self.mods:
				return 3
			else:
				return 1
	
	class MultiHoriz(MultiStroke): # A vertical stack of horizontals
		def draw(self, rend): # Modified from Renderer.draw_horizontal
			rend.draw_potential_damage(self.x, self.y, self.w, self.h, self.mods)
			rend.save_transforms()
			rend.rotate(-pi/2)
			rend.draw_general_mod(-self.y-self.h, self.x, self.h, self.w, self.heads(), self.n, self.mods)
			rend.untransform()
	class MultiVert(MultiStroke): # A horizontal stack of verticals
		def draw(self, rend):
			rend.draw_potential_damage(self.x, self.y, self.w, self.h, self.mods)
			rend.draw_general_mod(self.x, self.y, self.w, self.h, self.heads(), self.n, self.mods)
	
	def adjust_tree(self, tree): # This one actually does something here!
		# tree = tree.copy() TODO HOW TO COPY TREES - right now we just modify in place
		
		# First, we're going to put the Headless modifier on every stroke whose head is right up against a perpendicular one
		ahs = {node for node in tree.traverse() if isinstance(node, Horizontal)}
		avs = {node for node in tree.traverse() if isinstance(node, Vertical)}
		
		# We need to separate out the ones that are inside Tenu adjustments because they use a different coordinate system
		ts = {node for node in tree.traverse() if isinstance(node, Tenu)}
		ths = {node for t in ts for node in t.traverse() if isinstance(node, Horizontal)}
		tvs = {node for t in ts for node in t.traverse() if isinstance(node, Vertical)}
		
		ahs -= ths
		avs -= tvs
		
		# We do a Cartesian product here, which might end up becoming somewhat expensive, but it hasn't become a problem yet
		for hs, vs in ((ahs, avs), (ths, tvs)):
			for v in vs:
				v_epsilon = self.OVERLAP_EPSILON
				v_center = v.pos[0] + v.dims[0] / 2
				def collision(x, y):
					return v_center-v_epsilon < x < v_center+v_epsilon and v.pos[1] <= y <= v.pos[1]+v.dims[1]
				for h in hs:
					h_epsilon = h.dims[1] / 2
					h_center = h.pos[1] + h.dims[1] / 2
					if collision(h.pos[0], h_center-h_epsilon) and collision(h.pos[0], h_center+h_epsilon):
						h.mods.add(Modifier.INTERNAL_HEADLESS)
			
			# As above but inverted
			for h in hs:
				h_epsilon = self.OVERLAP_EPSILON
				h_center = h.pos[1] + h.dims[1] / 2
				def collision(y, x): # NOTE INVERSION FOR SYMMETRY: y,x not x,y
					return h_center-h_epsilon < y < h_center+h_epsilon and h.pos[0] <= x <= h.pos[0]+h.dims[0]
				for v in vs:
					v_epsilon = v.dims[0] / 2
					v_center = v.pos[0] + v.dims[0] / 2
					if collision(v.pos[1], v_center-v_epsilon) and collision(v.pos[1], v_center+v_epsilon):
						v.mods.add(Modifier.INTERNAL_HEADLESS)
			
			# Now we see if we beheaded a stroke that's right after another stroke in the same direction—if so we need to ensure the head is drawn, or else it won't be visible at all
			epsilon2 = self.HEADTAIL_EPSILON ** 2 # Universal one this time since we're comparing a single point for each stroke
			def close(first, second):
				return (first[0]-second[0])**2 + (first[1]-second[1])**2 < epsilon2
			
			endpts = {(v.pos[0]+v.dims[0]/2, v.pos[1]+v.dims[1]) for v in vs} # Bottom center of each vertical
			for v in vs:
				if Modifier.INTERNAL_HEADLESS not in v.mods: continue # This is only a problem for headless strokes
				head = (v.pos[0]+v.dims[0]/2, v.pos[1]) # Top center
				for tail in endpts:
					if close(head, tail):
						trim = min(v.dims[0]/2, self.COLLISION_TRIM)
						# We add this amount to y and subtract it from h
						# To effectively move the stroke right by that amount
						v.pos = (v.pos[0], v.pos[1]+trim)
						v.dims = (v.dims[0], v.dims[1]-trim)
						v.mods -= {Modifier.INTERNAL_HEADLESS}
						# These modifications can get overwritten by the later groupings, potentially, but it's not a problem if so—the grouping code requires the same mods on all of them, so they'll all be not-headless, and thus the big head will be clear enough
						# TODO but if this is the start of a new group, will it result in the positioning being wrong?
						break
			
			endpts = {(h.pos[0]+h.dims[0], h.pos[1]+h.dims[1]/2) for h in hs} # Center right of each horizontal
			for h in hs:
				if Modifier.INTERNAL_HEADLESS not in h.mods: continue
				head = (h.pos[0], h.pos[1]+h.dims[1]/2) # Center left
				for tail in endpts:
					if close(head, tail):
						trim = min(h.dims[1]/2, self.COLLISION_TRIM)
						h.pos = (h.pos[0]+trim, h.pos[1])
						h.dims = (h.dims[0]-trim, h.dims[1])
						h.mods -= {Modifier.INTERNAL_HEADLESS}
						break
		
		# Now, we go through and consolidate groups of adjacent parallel strokes
		hstacks = [node for node in tree.traverse() if isinstance(node, HStack)]
		vstacks = [node for node in tree.traverse() if isinstance(node, VStack)]
		
		for hstack in hstacks:
	#		print('Parsing hstack')
			new = []
			current = None
			for child in hstack.contents:
				if isinstance(child, Vertical):
	#				print('\tFound vertical')
					if current is None:
						current = self.MultiVert(*child.pos, *child.dims, 1, child.mods)
					elif current.mods != child.mods:
						new.append(current)
						current = self.MultiVert(*child.pos, *child.dims, 1, child.mods)
					else: # Mods are compatible!
						current.n += 1 # Increase number of tails
						current.w = (child.pos[0] + child.dims[0]) - current.x # Set width so the right edge is our new stroke's right edge
				else:
	#				print('\tFound non-vertical')
					if current is not None: new.append(current)
					current = None
					new.append(child)
			if current is not None: new.append(current)
			hstack.contents = new # Replace the old children with the new ones
		
		for vstack in vstacks:
	#		print('Parsing vstack')
			new = []
			current = None
			for child in vstack.contents:
				if isinstance(child, Horizontal):
	#				print('\tFound horizontal')
					if current is None:
						current = self.MultiHoriz(*child.pos, *child.dims, 1, child.mods)
					elif current.mods != child.mods:
						new.append(current)
						current = self.MultiHoriz(*child.pos, *child.dims, 1, child.mods)
					else: # Mods are compatible!
						current.n += 1 # Increase number of tails
						current.h = (child.pos[1] + child.dims[1]) - current.y # Set height so the bottom edge is our new stroke's bottom edge
				else:
	#				print('\tFound non-horizontal')
					if current is not None: new.append(current)
					current = None
					new.append(child)
			if current is not None: new.append(current)
			vstack.contents = new # Replace the old children with the new ones
		
		return tree
	
	def draw_general_mod(self, x, y, w, h, heads, tails, mods):
		# Handle common modifiers and then delegate to draw_general; makes things easier for MultiStroke
		
		if Modifier.INTERNAL_DIAGONAL in mods:
			adj_amount = h * (1-1/sqrt(2))
			if Modifier.HEADSHORT in mods and Modifier.TAILSHORT in mods:
				adj_amount /= 2
		else:
			adj_amount = h/3
		
		if Modifier.HEADSHORT in mods:
			h -= adj_amount
			y += adj_amount
		if Modifier.TAILSHORT in mods:
			h -= adj_amount
		
		self.draw_general(x, y, w, h, heads, tails, mods)
	
	def draw_general(self, x, y, w, h, heads, tails, mods):
		# Draw a stroke with any number of heads and tails - this only happens in the ink renderer which tries to consolidate parallel strokes together!
		c = self.ctx
		c.save()
		c.translate(x, y) # Make sure we don't have to worry about x and y ever again
		
		headless = Modifier.INTERNAL_HEADLESS in mods
		amphisbaena = Modifier.INTERNAL_BOTHWAYS in mods
		
		tailstride = w / (tails+1) # How far apart each tail should be placed
		headstride = min(self.HEAD_SEPARATION, h/(heads+1)) # And for the heads; don't let this exceed HEAD_SEPARATION
	#	print('Stride:', tailstride, headstride)
		
		center = -3/2 * w # Center of the circle we're drawing our arc from is at (w/2, center)
		theta = atan((w/2) / center) # The angle that the arc goes in **each** direction (so total arc is 2*theta)
		radius = sqrt(center**2 + (w/2)**2) # The radius of that circle
		
		def get_dy(dx): # Given the horizontal distance from the left edge to one of the tails, get the vertical distance to the top of that tail
			if headless: return 0 # If there's no rounded head to align with, don't bother to!
	#		print('Distance from left edge:', dx)
			xx = w/2 - dx # Change "distance from left edge" to "distance from center line"
	#		print('Distance from center line:', xx)
			# Now the point xx, yy is on the circle with radius `radius` and center `center`
			# So xx**2 + yy**2 = radius**2
			yy = sqrt(radius**2 - xx**2)
	#		print('Distance from circle center:', yy)
	#		print('Radius:', radius)
			# And yy = center + dy
			# Since the top line is `center` down from the center point
			dy = yy - (-center)
	#		print('Distance from top line:', dy)
			return dy
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		
		# Draw `heads` heads
		for i in range(heads):
			if i==0 and headless: continue
			cc = (w/2, center+i*headstride)
			c.move_to(w, i*headstride)
			c.arc(*cc, radius, pi/2+theta, pi/2-theta)
		
		# Draw the opposite head, if needed
		if amphisbaena:
			cc = (w/2, h-center)
			c.move_to(0, h)
			c.arc(*cc, radius, -pi/2+theta, -pi/2-theta)
		
		# Draw `tails` tails
		for i in range(tails):
			dx = (i+1)*tailstride
			dy = get_dy(dx)
			c.move_to(dx, dy)
			if amphisbaena:
				c.line_to(dx, h-dy)
			else:
				c.line_to(dx, h)
		
		c.set_line_cap(cairo.LineCap.ROUND)
		c.set_line_join(cairo.LineJoin.ROUND)
		
		c.stroke()
		
		c.restore()
	
	def draw_single(self, x, y, w, h, mods):
		self.draw_general(x, y, w, h, 1, 1, mods)
	def draw_double(self, x, y, w, h, mods):
		self.draw_general(x, y, w, h, 2, 1, mods)
	def draw_triple(self, x, y, w, h, mods):
		self.draw_general(x, y, w, h, 3, 1, mods)
	
	def draw_hook(self, x, y, w, h, mods): # Based on OneSidedRenderer but with round caps and joins - hakens don't seem to be attested in the inked tablets sadly so I have to extrapolate
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		ne = (w, 0)
		se = (w, h)
		w = (0, h/2)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*ne)
		c.line_to(*w)
		c.line_to(*se)
		
		c.set_line_cap(cairo.LineCap.ROUND)
		c.set_line_join(cairo.LineJoin.ROUND)
		c.stroke()
		
		c.restore()

# Like an InkRenderer but with sharp points instead of rounded ones
class SharpInkRenderer(InkRenderer):
	
	# Taken straight from InkRenderer
	def draw_general(self, x, y, w, h, heads, tails, mods):
		c = self.ctx
		c.save()
		c.translate(x, y) # Make sure we don't have to worry about x and y ever again
		
		headless = Modifier.INTERNAL_HEADLESS in mods
		
		tailstride = w / (tails+1) # How far apart each tail should be placed
		headstride = min(self.HEAD_SEPARATION, h/(heads+1)) # And for the heads; don't let this exceed HEAD_SEPARATION
		
		center = -3/2 * w # Center of the circle we're drawing our arc from is at (w/2, center)
		radius = sqrt(center**2 + (w/2)**2)
		
		p1 = (center + radius) - self.strokewidth*0 # y-coordinate of a point on the upper arc
		p2 = (center + radius) + self.strokewidth*1 # And the lower
		# We err more on the lower side because the upper side can cause problems if it "overflows" (if the point chosen is above the midline so the circle flips upside down)
		
		# Now imagine a circle passing through three points
		# (-x, 0), (0, p), (x, 0)
		# Its center lies at (0, y)
		# We now know that (x-0)**2 + (0-y)**2 - r**2 = 0
		# And (0-0)**2 + (p-y)**2 - r**2 = 0
		# i.e. p**2 - 2*p*y + y**2 - r**2 = 0
		# Subtracting these equations, we see that
		# x**2 - p**2 + 2*p*y = 0
		# Thus, y = (p**2 - x**2) / 2*p
		center1 = (p1**2 - (w/2)**2) / (2*p1)
		center2 = (p2**2 - (w/2)**2) / (2*p2)
		# So we now have the y-coordinates 
		radius1 = -center1 + p1 # Since center < 0
		radius2 = -center2 + p2
		
	#	print('p:', p1, p2, p1-p2)
	#	print('center:', center1, center2, center1-center2)
	#	print('radius:', radius1, radius2, radius1-radius2)
		
		theta1 = atan((w/2) / center1)
		theta2 = atan((w/2) / center2)
		
		def get_dy(dx): # Given the horizontal distance from the left edge to one of the tails, get the vertical distance to the top of that tail
			if headless: return 0 # If there's no rounded head to align with, don't bother to!
			xx = w/2 - dx # Change "distance from left edge" to "distance from center line"
			# Now the point xx, yy is on the circle with radius `radius` and center `center`
			# So xx**2 + yy**2 = radius**2
			yy = sqrt(radius**2 - xx**2)
			# And yy = center + dy
			# Since the top line is `center` down from the center point
			dy = yy - (-center)
			return dy
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		
		# Draw `heads` heads
		for i in range(heads):
			if i==0 and headless: continue
			cc1 = (w/2, center1+i*headstride)
			cc2 = (w/2, center2+i*headstride)
	#		c.move_to(w, i*headstride)
			c.arc(*cc1, radius1, pi/2+theta1, pi/2-theta1)
			c.arc_negative(*cc2, radius2, pi/2-theta2, pi/2+theta2)
			c.fill()
		
		# Draw `tails` tails
		for i in range(tails):
			dx = (i+1)*tailstride
			
			dx1 = dx - self.strokewidth/2
			dx2 = dx + self.strokewidth/2
			
			dy1 = get_dy(dx1)
			dy2 = get_dy(dx2)
			
			c.move_to(dx, h) # Tip
			c.line_to(dx1, dy1)
			c.line_to(dx2, dy2)
			c.line_to(dx, h)
			c.fill()
		
		c.restore()
	
	# Taken from LinearRenderer
	def draw_hook(self, x, y, w, h, mods):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		ne = (w, 0)
		se = (w, h)
		_w = (0, h/2)
		_c = (self.strokewidth, h/2)
		
		self.begin_drawing((Modifier.HIGHLIGHT in mods))
		c.move_to(*ne)
		c.line_to(*_c)
		c.line_to(*se)
		c.line_to(*_w)
		c.line_to(*ne)
		c.fill()
		
		c.restore()

def test_twosided():
	rend = TwoSidedRenderer(256, 256, format='svg', hlcolor='gold', fill=False)
	rend.blank()
	rend.draw_vertical(0.25, 0.25, 0.25, 0.5, mods={Modifier.TRIPLE})
	rend.draw_horizontal(0.25*1.5, 0.25*2.5, 0.25, 0.25)
	rend.draw_hook(0.125, 0.25*1.5, 0.125, 0.25, mods={Modifier.HIGHLIGHT})
	rend.hatch(0.25, 0.25, 0.5, 0.5)
	rend.hatch(0.3446, 0.33, 0.25, 0.5, True)
	rend.show()

def test_ink():
	rend = InkRenderer(256, 256, format='svg', strokewidth=0.05)
	rend.blank()
	rend.draw_general(0, 1/3, 1/3, 1/2, 3, 3, set())
	rend.draw_general(1/3, 1/3, 2/3, 1/2, 3, 3, {Modifier.INTERNAL_BOTHWAYS})
	rend.show()

if __name__ == '__main__':
	test_ink()

import subprocess as sp
from math import pi, atan, cos, sqrt
from time import sleep
from contextlib import contextmanager
from io import StringIO, BytesIO

import cairo
from PIL.ImageColor import getrgb

try:
	from elements import Modifier
except ImportError:
	from .elements import Modifier

DRAW_BOXES = False

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

class Renderer:
	def __init__(self, width, height, skip=False, format='png', bgcolor=None, fgcolor=None, hlcolor=None):
		self.format = format
		if format == 'svg':
			self.buffer = BytesIO()
			self.surf = cairo.SVGSurface(self.buffer, width, height)
		elif format == 'png':
			self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
		elif format == 'pdf':
			self.buffer = BytesIO()
			self.surf = cairo.PDFSurface(self.buffer, width, height)
		else:
			raise ValueError('Unrecognized format', format)
		
		self.bgcolor = colorparse(bgcolor) or (0.1, 0.1, 0.1, 1)
		self.fgcolor = colorparse(fgcolor) or (1, 1, 1, 1)
		self.hlcolor = colorparse(hlcolor) or (0, 1, 0, 1)
		
		self.ctx = cairo.Context(self.surf)
		if not skip:
			self.ctx.scale(width, height)
			self.blank()
	
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
	
	def blank(self):
		self.ctx.set_source_rgba(*self.bgcolor)
		self.ctx.rectangle(0, 0, 1, 1)
		self.ctx.fill()
	
	def begin_drawing(self, highlight=False):
		if highlight: self.ctx.set_source_rgba(*self.hlcolor)
		else: self.ctx.set_source_rgba(*self.fgcolor)
		self.ctx.set_line_width(0.01)
	
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
	
	def draw_single(self, x, y, w, h, mods):
		raise NotImplementedError() # To be implemented in derived classes
	
	def draw_double(self, x, y, w, h, mods):
		raise NotImplementedError() # Same
	
	def draw_triple(self, x, y, w, h, mods):
		raise NotImplementedError() # Same
	
	def draw_hook(self, x, y, w, h, mods):
		raise NotImplementedError() # Same
	
	def draw_stroke(self, x, y, w, h, mods):
		adj_amount = h/3
		if Modifier.HEADSHORT in mods:
			h -= adj_amount
			y += adj_amount
		if Modifier.TAILSHORT in mods:
			h -= adj_amount
		
		if Modifier.DOUBLE in mods: self.draw_double(x, y, w, h, mods)
		elif Modifier.TRIPLE in mods: self.draw_triple(x, y, w, h, mods)
		else: self.draw_single(x, y, w, h, mods)
	
	def draw_wildcard(self, x, y, w, h, mods): # Draw a box with an X in it; this is the same between all the different renderers
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
	
	def draw_vertical(self, x, y, w, h, mods=()):
		self.draw_stroke(x, y, w, h, mods)
	
	def draw_horizontal(self, x, y, w, h, mods=()):
		self.ctx.save()
		self.ctx.rotate(-pi/2)
		
		self.draw_stroke(-y-h, x, h, w, mods)
		
		self.ctx.restore()
	
	def draw_downward(self, x, y, w, h, mods=()):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		theta = atan(h/w)
		phi = (pi/2) - theta
		
		# I need to attach a diagram to make this all make sense...
		head = min(h, 1/3) # The width of the stroke head
		diag = sqrt(w**2 + h**2)
		
		if h > w:
			x2 = head / (2*cos(phi))
			y2 = 0
			x3 = -head
			cutoff = (head*w) / (2*h)
		else:
			x2 = 0
			y2 = head / (2*cos(theta))
			x3 = 0
			cutoff = (head*h) / (2*w)
		
		stroke = diag - cutoff
		
		c.translate(x2, y2) # Set the new origin point
		c.rotate(-phi)
		c.translate(x3, 0)
		self.draw_stroke(0, 0, head, stroke, mods)
		c.restore()
	
	def draw_upward(self, x, y, w, h, mods=()):
		self.ctx.save()
		self.ctx.translate(x, y)
		self.ctx.scale(1, -1) # Invert vertical axis
		self.ctx.translate(0, -h)
		
		mods = set(mods) ^ {Modifier.INTERNAL_FLIP} # Since we flipped one of the axes we should unflip it for rendering
		self.draw_downward(0, 0, w, h, mods) # Delegate to downward
		
		self.ctx.restore()
	
	@classmethod
	def render(cls, root, highlight=(), scale=512, margin=32, justify=None, *args, **kwargs): # Any additional parameters are passed to the class constructor
		# `justify` is unused but it's very convenient to have this and `render_sequence` have the same signature
		root.propagate_dimensions()
		root.apply_highlighting(highlight)
		
		width = int(scale*root.dims[0] + 2*margin)
		height = int(scale*root.dims[1] + 2*margin)
		rend = cls(width, height, skip=True, *args, **kwargs)
		
		# Manual blanking
		rend.ctx.set_source_rgba(*rend.bgcolor)
		rend.ctx.rectangle(0, 0, width, height)
		rend.ctx.fill()
		
		rend.ctx.save()
		
		rend.ctx.translate(margin, margin)
		rend.ctx.scale(scale, scale)
		root.draw(rend)
		
		rend.ctx.restore()
		return rend
	
	def render_sign_at(self, sign, x, y):
		self.ctx.save()
		self.ctx.translate(x, y)
		sign.draw(self)
		self.ctx.restore()
	
	def render_sign_row(self, row, y, offset):
		x = offset / self.scale
		scaled_margin = self.margin / self.scale # We've scaled the canvas so that 1 unit = scale pixels, therefore margin pixels = margin/scale units
		for sign in row:
			x += scaled_margin
			self.render_sign_at(sign, x, y)
			x += sign.dims[0] # Sign width
	
	def render_sign_rows(self, rows, offsets):
		y = 0
		scaled_margin = self.margin / self.scale # See above
		for row, offset in zip(rows, offsets):
			y += scaled_margin
			self.render_sign_row(row, y, offset)
			y += 1 # Sign height (fixed)
	
	@classmethod
	def render_sequence(cls, rows, highlight=(), scale=512, margin=32, justify='c', *args, **kwargs): # As above re additional parameters
		# This time, `highlight` is the one that's ignored but included in order to make signatures line up
		row_widths = []
		for row in rows:
			for sign in row:
				sign.propagate_dimensions()
			# Now measure this row
			width = (
				sum(sign.dims[0] for sign in row)*scale # Signs
				+ margin * (len(row)+1) # Margins
			)
			row_widths.append(width)
		max_width = max(row_widths)
		height = scale * len(rows) + margin * (len(rows)+1)
		
		rend = cls(int(max_width), int(height), skip=True, *args, **kwargs)
		rend.scale = scale
		rend.margin = margin
		
		if justify == 'c':
			offsets = [(max_width-width)/2 for width in row_widths]
		elif justify == 'r':
			offsets = [(max_width-width) for width in row_widths]
		else:
			offsets = [0 for width in row_widths]
		
		# Manual blanking
		rend.ctx.set_source_rgba(*rend.bgcolor)
		rend.ctx.rectangle(0, 0, max_width, height)
		rend.ctx.fill()
		
		rend.ctx.save()
		rend.ctx.scale(scale, scale)
		rend.render_sign_rows(rows, offsets)
		rend.ctx.restore()
		
		return rend
	
	@contextmanager
	def tenu(self, pos, dims): # Tilt the whole canvas sideways temporarily
		c = self.ctx
		c.save()
		
		x, y = pos
		w, h = dims
		
		c.translate(x, y+h/2)
		c.rotate(-pi/4)
		c.translate(0, 0)
		
		yield self # This is where the other rendering happens
		
		c.restore() # Un-tenu-fy the canvas again

class OneSidedRenderer(Renderer):
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

class TwoSidedRenderer(Renderer):
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
		c.move_to(*w_)
		c.line_to(*e)
		c.arc_negative(*pivot2r, r, -pi/2, pi)
		c.arc_negative(*pivot2l, r, 0, -pi/2)
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
		c.move_to(*w_)
		c.line_to(*e)
		c.arc_negative(*pivot2r, r, -pi/2, pi)
		c.arc_negative(*pivot2l, r, 0, -pi/2)
		c.move_to(*w2)
		c.line_to(*e2)
		c.arc_negative(*pivot3r, r, -pi/2, pi)
		c.arc_negative(*pivot3l, r, 0, -pi/2)
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
		c.stroke()
		
		c.restore()

class LinearRenderer(Renderer):
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
	
	def draw_downward(self, x, y, w, h, mods=()): # We override this method too, because with the linear renderer we can get closer to the corners without the head getting in the way
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

if __name__ == '__main__':
	rend = TwoSidedRenderer(256, 256, format='pdf', hlcolor='gold')
	rend.blank()
	rend.draw_vertical(0.25, 0.25, 0.25, 0.5, mods={Modifier.TRIPLE})
	rend.draw_horizontal(0.25*1.5, 0.25*2.5, 0.25, 0.25)
	rend.draw_hook(0.125, 0.25*1.5, 0.125, 0.25, mods={Modifier.HIGHLIGHT})
	rend.show()

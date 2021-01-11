import subprocess as sp
from math import pi, atan, cos, sqrt
from time import sleep
from contextlib import contextmanager

import cairo

from elements import Modifier

DRAW_BOXES = False

class Renderer:
	def __init__(self, width, height, skip=False):
		self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
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
		
		self.ctx.set_source_rgba(*col, 0.25)
		self.ctx.rectangle(x, y, w, h)
		self.ctx.fill()
	
	def blank(self):
		self.ctx.set_source_rgba(0.1, 0.1, 0.1, 1)
		self.ctx.rectangle(0, 0, 1, 1)
		self.ctx.fill()
	
	def begin_drawing(self):
		self.ctx.set_source_rgba(1, 1, 1, 1)
		self.ctx.set_line_width(0.01)
	
	def show(self):
	#	with NamedTemporaryFile(suffix='.png') as f:
		with open('tmp.png', 'wb') as f:
	#		fn = f.name
			fn = 'tmp.png'
			self.surf.write_to_png(fn)
			sp.run(['xdg-open', fn])
	#		sleep(0.25)
	
	def draw_single(self, x, y, w, h):
		raise NotImplemented() # To be implemented in derived classes
	
	def draw_double(self, x, y, w, h):
		raise NotImplemented() # Same
	
	def draw_hook(self, x, y, w, h):
		raise NotImplemented() # Same
	
	def draw_stroke(self, x, y, w, h, double, mods):
		adj_amount = h/3
		if Modifier.HEADSHORT in mods:
			h -= adj_amount
			y += adj_amount
		if Modifier.TAILSHORT in mods:
			h -= adj_amount
		
		if double: self.draw_double(x, y, w, h)
		else: self.draw_single(x, y, w, h)
	
	def draw_vertical(self, x, y, w, h, double=False, mods=()):
		self.draw_stroke(x, y, w, h, double, mods)
	
	def draw_horizontal(self, x, y, w, h, double=False, mods=()):
		self.ctx.save()
		self.ctx.rotate(-pi/2)
		
		self.draw_stroke(-y-h, x, h, w, double, mods)
		
		self.ctx.restore()
	
	def draw_downward(self, x, y, w, h, double=False, mods=()):
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
		self.draw_stroke(0, 0, head, stroke, double, mods)
		c.restore()
	
	def draw_upward(self, x, y, w, h, double=False, mods=()):
		self.ctx.save()
		self.ctx.translate(x, y)
		self.ctx.scale(1, -1) # Invert vertical axis
		self.ctx.translate(0, -h)
		
		self.draw_downward(0, 0, w, h, double, mods) # Delegate to downward
		
		self.ctx.restore()
	
	@classmethod
	def render(cls, root, scale=512, margin=32):
		root.propagate_dimensions()
		
		width = int(scale*root.dims[0] + 2*margin)
		height = int(scale*root.dims[1] + 2*margin)
		rend = cls(width, height, skip=True)
		
		# Manual blanking
		rend.ctx.set_source_rgba(0.1, 0.1, 0.1, 1)
		rend.ctx.rectangle(0, 0, width, height)
		rend.ctx.fill()
		
		rend.ctx.save()
		
		rend.ctx.translate(margin, margin)
		rend.ctx.scale(scale, scale)
		root.draw(rend)
		
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
	def draw_single(self, x, y, w, h):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		nw = (0, 0)
		ne = (w, 0)
		pivot = (w, w/2)
		r = w/2
		mid = (w/2, w/2)
		s = (w/2, h)
		
		self.begin_drawing()
		c.move_to(*nw)
		c.line_to(*ne)
		c.arc_negative(*pivot, r, -pi/2, pi)
		c.move_to(*mid)
		c.line_to(*s)
		c.stroke()
		
		c.restore()
	
	def draw_double(self, x, y, w, h):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		nw = (0, 0)
		ne = (w, 0)
		pivot1 = (w, w/2)
		w_ = (0, w/2)
		e = (w, w/2)
		pivot2 = (w, w)
		r = w/2
		mid = (w/2, w)
		s = (w/2, h)
		
		self.begin_drawing()
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
	
	def draw_hook(self, x, y, w, h):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		ne = (w, 0)
		se = (w, h)
		w = (0, h/2)
		
		self.begin_drawing()
		c.move_to(*ne)
		c.line_to(*w)
		c.line_to(*se)
		c.stroke()
		
		c.restore()
	
	# TODO: Upward strokes are currently inverted, should fix somehow

class TwoSidedRenderer(Renderer):
	def draw_single(self, x, y, w, h):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		nw = (0, 0)
		ne = (w, 0)
		pivot1 = (w, w/2)
		pivot2 = (0, w/2)
		r = w/2
		mid = (w/2, w/2)
		s = (w/2, h)
		
		self.begin_drawing()
		c.move_to(*nw)
		c.line_to(*ne)
		c.arc_negative(*pivot1, r, -pi/2, pi)
		c.arc_negative(*pivot2, r, 0, -pi/2)
		c.move_to(*mid)
		c.line_to(*s)
		c.stroke()
		
		c.restore()
	
	def draw_double(self, x, y, w, h):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
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
		
		self.begin_drawing()
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
	
	def draw_hook(self, x, y, w, h):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		ne = (w, 0)
		se = (w, h)
		w = (0, h/2)
		
		self.begin_drawing()
		c.move_to(*ne)
		c.line_to(*w)
		c.line_to(*se)
		c.curve_to(*se, *w, *ne)
		c.stroke()
		
		c.restore()

class LinearRenderer(Renderer):
	WIDTH = 0.1
	
	def draw_single(self, x, y, w, h):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		m = w/2 # Midpoint
		nw = (m-self.WIDTH/2, 0)
		ne = (m+self.WIDTH/2, 0)
		s = (m, h+0.01)
		
		self.begin_drawing()
		c.move_to(*nw)
		c.line_to(*ne)
		c.line_to(*s)
		c.line_to(*nw)
		c.fill()
		
		c.restore()
	
	def draw_double(self, x, y, w, h):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		m = w/2 # Midpoint
		nw = (m-self.WIDTH/2, 0)
		ne = (m+self.WIDTH/2, 0)
		_c = (m, h*0.25)
		_w = (m-self.WIDTH/2, h*0.25)
		_e = (m+self.WIDTH/2, h*0.25)
		s = (m, h+0.01)
		
		self.begin_drawing()
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
	
	def draw_hook(self, x, y, w, h):
		c = self.ctx
		c.save()
		c.translate(x, y)
		
		ne = (w, 0)
		se = (w, h)
		_w = (0, h/2)
		_c = (self.WIDTH, h/2)
		
		self.begin_drawing()
		c.move_to(*ne)
		c.line_to(*_c)
		c.line_to(*se)
		c.line_to(*_w)
		c.line_to(*ne)
		c.fill()
		
		c.restore()
	
	def draw_downward(self, x, y, w, h, double=False): # We override this method too, because with the linear renderer we can get closer to the corners without the head getting in the way
		c = self.ctx
		c.save()
		c.translate(x, y)
		theta = pi/2 - atan(h/w)
		c.rotate(-theta)
		c.translate(-self.WIDTH/2, 0)
		hyp = sqrt(w**2+h**2)
		self.draw_stroke(0, 0, self.WIDTH, hyp, double)
		c.restore()

if __name__ == '__main__':
	rend = TwoSidedRenderer(256, 256)
	rend.blank()
	rend.draw_vertical(0.25, 0.25, 0.25, 0.5, double=True)
	rend.draw_horizontal(0.25*1.5, 0.25*2, 0.25, 0.25)
	rend.draw_hook(0.125, 0.25*1.5, 0.125, 0.25)
	rend.show()

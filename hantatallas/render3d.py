from io import StringIO
from math import pi
import subprocess as sp

from render import Renderer
from elements import Modifier

class ScadRenderer(Renderer):
	def __init__(self, width, height, margin=0, scale=0, thickness=None, *args, **kwargs): # TODO remove args and kwargs
		super().__init__(width, height, margin=margin, scale=scale) # This fills out the basic layout parameters like fullwidth and fullheight
		
		self.buffer = StringIO()
		
		self.depth = 0
		self.depthstack = [] # This is used to imitate Cairo's context save and restore, which is also a stack: here, it holds how many nested levels deep we are
		
		if thickness is None: thickness = min(width, height) / 2
		
		self.record('use <../3dmodel/cuneiform.scad>\n') # Import the files we need for this
		
		self.rescale(1, -1) # Invert the y-axis to match what Cairo does
		
		self.record('difference(){')
		self.depth += 1
		self.record(f'translate([0,0,{-thickness}])')
		self.record(f'\tcube([{self.fullwidth},{self.fullheight},{thickness}]);')
		self.record('union(){')
		self.depth += 1
		
		self.setup_scaling()
	
	def record(self, s): # Convenience method for writing to the buffer
		self.buffer.write('\t'*self.depth + s + '\n')
	
	def save_transforms(self):
		self.depthstack.append(self.depth)
	
	def untransform(self):
		goal = self.depthstack.pop()
		while self.depth > goal:
			self.depth -= 1
			self.record('}')
	
	def rotate(self, theta):
		theta *= 180/pi # Radians to degrees
		self.record(f'rotate({theta}){{')
		self.depth += 1
	
	def translate(self, x, y):
		self.record(f'translate([{x},{y},0]){{')
		self.depth += 1
	
	def rescale(self, xs, ys):
		if xs == ys: zs = xs
		else: zs = 1 # Decide what to do with the Z axis based on whether we're scaling evenly or unevenly
		self.record(f'scale([{xs},{ys},{zs}]){{')
		self.depth += 1
	
	def finish(self):
		while self.depth:
			self.depth -= 1
			self.record('}')
		return self.buffer.getvalue()
	
	def result(self):
		return self.buffer.getvalue()
	
	def show(self):
		if self.depth: self.finish()
		with open('tmp.scad', 'w') as f:
			f.write(self.buffer.getvalue())
		sp.run(['xdg-open', 'tmp.scad'])
	
	def _old_draw_single(self, x, y, w, h, mods):
		self.save_transforms()
		self.translate(x, y)
		if Modifier.INVERT in mods:
			self.rescale(0, -1)
			self.translate(0, -h)
		self.record(f'wedge({w/2}, 0, 0, {w}, {h}, 0);')
		self.untransform()
	
	def draw_single(self, x, y, w, h, mods):
		self.record(f'singlestroke({x}, {y}, {w}, {h});')
	
	def draw_double(self, x, y, w, h, mods):
		self.record(f'doublestroke({x}, {y}, {w}, {h});')
	
	def draw_triple(self, x, y, w, h, mods):
		self.record(f'triplestroke({x}, {y}, {w}, {h});')
	
	def draw_hook(self, x, y, w, h, mods):
		self.record(f'hookstroke({x}, {y}, {w}, {h});')
	
	def draw_rule(self, y, w):
		self.record(f'hrule({y}, {w});')
	
	def hatch(self, x, y, w, h, highlight=False):
		self.record(f'hatcharea({x}, {y}, {w}, {h});')

if __name__ == '__main__':
	from parser import parse
	ScadRenderer.render(parse("W[{0[hc]h}v{h[vv2]Mh}v]"), scale=10, margin=1, thickness=2.5).show()

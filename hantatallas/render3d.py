from io import StringIO
from math import pi
import subprocess as sp

from render import Renderer
from elements import Modifier, Winkelhaken, Vertical

tau = 2*pi # I am obstinate

def remap(val1, lo1, hi1, lo2, hi2): # Remap `val` from the range `lo1-hi1` to the range `lo2-hi2`
	range1 = hi1 - lo1
	range2 = hi2 - lo2
	normalized = (val1 - lo1) / range1
	val2 = (normalized * range2) + lo2
	return val2

class ScadRenderer(Renderer):
	def __init__(self, width, height, margin=0, scale=0, thickness=None, shape='tablet', multiplex=1, ridge=5, extramargin=3, *args, **kwargs): # TODO remove args and kwargs
		super().__init__(width, height, margin=margin, scale=scale) # This fills out the basic layout parameters like fullwidth and fullheight
		
		self.buffer = StringIO()
		
		self.multiplex = multiplex # Multiple copies of one text, if the text is too small
		self.ridge = ridge
		self.extramargin = extramargin
		
		self.depth = 0
		self.depthstack = [] # This is used to imitate Cairo's context save and restore, which is also a stack: here, it holds how many nested levels deep we are
		self.shape = shape
		
		if thickness is None: thickness = min(width, height) / 2
		
		self.record('include <../3dmodel/cuneiform.scad>\n') # Import the files we need for this
		# Using `include` instead of `use` we can override MAX_STROKE_WIDTH later if we want
		
		if shape == 'stamp': # The imprints will be *positives*
			self.rescale(1, -1) # Invert the y-axis to match what Cairo does
			self.record('rotate([0,180,0])') # Flip it around so the positives go up instead of down
			self.record('union(){') # We're going to start with a thin plate to attach the stamp to
			self.depth += 1
			self.record(f'cube([{self.fullwidth},{self.fullheight},{thickness}]);') # This is our plate
			self.record('difference(){') # Now we're going to subtract the "air" (above the surface) from the styli
			self.depth += 1
			self.save_transforms()
			self.record('union(){')
			self.depth += 1
		
		elif shape == 'seal': # As above, except wrapped around into a ring
			ridgesize = self.scale/self.ridge if self.ridge else 0
			extramargin = self.scale/self.extramargin if self.extramargin else 0
			self.fullwidth += extramargin + ridgesize # Add an extra margin on the right
			
			outerdepth = self.scale / 3 # How much beyond the surface we should try to capture in the cylinder
			
			if thickness < 0:
				print('Thickness:', thickness)
				print('Circumference:', self.fullwidth*self.multiplex)
				print('Outer radius:', (self.fullwidth*self.multiplex / tau))
				print('Inner radius:', -thickness)
				thickness = (self.fullwidth*self.multiplex / tau) - (-thickness) # Make sure the hole in the middle of the seal has a radius of `-thickness` - outer circumference is fullwidth, so outer radius is fullwidth/τ, and thus thickness should be outer radius minus inner radius
				print('Result:', thickness)
				thickness -= outerdepth
				print('Adjusted:', thickness)
			
			self.record('use <../3dmodel/cylinder.scad>\n')
	#		if self.multiplex > 1: # For the doubleseal version
			self.record('module part(){')
			
			self.record(f'cylindrify({self.fullwidth * self.multiplex}, {self.fullheight}, {outerdepth}, 50*($preview?1:10))') # TODO PARAMETRIZE third is height of stamp fourth is number of segments in ring (lowered for preview, raised for render)
			# A couple transforms to set this into the position cylindrify wants
			self.record('rotate([0,0,90])')
			self.record(f'translate([{self.fullwidth}, 0, 0])')
			self.rescale(1, -1) # Invert the y-axis to match what Cairo does
			# And now it's the same as 'stamp'
			self.record('rotate([0,180,0])') # Flip it around so the positives go up instead of down
			
			self.record('union(){') # We're going to start with a thin plate to attach the stamp to
			self.depth += 1
			self.record(f'cube([{self.fullwidth},{self.fullheight},{thickness if thickness > 0 else f"/* {thickness} */ 1"}]);') # This is our plate
			self.record('difference(){') # Now we're going to subtract the "air" (above the surface) from the styli
			self.depth += 1
			
			self.save_transforms()
			self.record('union(){')
			self.depth += 1
			
			self.record(f'vrule({self.fullwidth-self.scale/6-ridgesize}, {self.fullheight}, {ridgesize});') # Experiment: put a ridge along one side to mark the start/end
			self.record(f'edgerule(0, {self.fullwidth}, {ridgesize}, true);') # Similarly, ridge at top edge
			self.record(f'edgerule({self.fullheight}, {self.fullwidth}, {ridgesize}, false);') # And bottom edge
		
		elif shape == 'tablet': # The imprints will be *negatives*
			self.rescale(1, -1) # Invert the y-axis to match what Cairo does
			self.record('difference(){') # We're going to subtract the styli from the clay
			self.depth += 1
			self.record(f'translate([0,0,{-thickness}])')
			self.record(f'\tcube([{self.fullwidth},{self.fullheight},{thickness}]);') # This is our tablet itself, placed just under the XY plane
			self.record('union(){')
			self.depth += 1
		
		else:
			raise ValueError('Not a valid shape', shape)
		
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
		if self.shape == 'stamp' or self.shape == 'seal': # We need to subtract the "air" from the styli afterward if we're in stamp mode
			while self.depthstack: self.untransform() # Go back to the very first entry of the depth stack, which should be the one we made at the very beginning
			self.record(f'cube([{self.fullwidth},{self.fullheight},100]);') # TODO PARAMETRIZE THIS
		
		while self.depth:
			self.depth -= 1
			self.record('}')
		
	#	if self.multiplex == 1: # We put this in a module definition, so we should now invoke the module
		if self.shape == 'seal':
			self.record('}')
			self.record('')
			for i in range(self.multiplex):
				self.record(f'rotate([0,0,{i*360/self.multiplex}]) part();')
		
		if self.shape == 'stamp' or self.shape == 'seal': # We want thicker strokes if it's a positive rather than a negative
			self.record('')
			self.record('MAX_STROKE_WIDTH = 1/3;')
		
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
		if h > 0.5: # When hooks are too big they go a lot deeper than any other stroke, so we have a "factor" argument we can reduce if they do
			factor = remap(h, 0.5, 1, 0.75, 0.9)
			self.record(f'hookstroke({x}, {y}, {w}, {h}, {factor});')
		else: # Default is 0.75; 1 means perfectly flat against the surface, so larger factors are shallower
			self.record(f'hookstroke({x}, {y}, {w}, {h});')
	
	def draw_rule(self, y, w):
		self.record(f'hrule({y}, {w});')
	
	def hatch(self, x, y, w, h, highlight=False):
		self.record(f'hatcharea({x}, {y}, {w}, {h});')
	
	def adjust_tree(self, tree): # We actually do make some tree adjustments here, because [cv] puts the winkelhaken too close to the vertical for 3D printing purposes
		hooks = (s for s in tree.traverse_strokes() if isinstance(s, Winkelhaken)) # An iterator of all the hooks in this tree
		def is_vert(s): return isinstance(s, Vertical) # Two lambdas given names for readability
		def is_block(s): return isinstance(s, Winkelhaken) or isinstance(s, Vertical)
		for hook in hooks:
	#		print('Loop')
			x, y = hook.pos
			w, h = hook.dims
			cx, cy = x+w/2, y+h/2 # Center
			l1 = cx-0.45*w, cy # A point on the inner left edge
			l2 = cx-0.55*w, cy # A point on the outer left edge
			r1 = cx+0.45*w, cy # Inner right
			r2 = cx+0.55*w, cy # Outer right
			
			left_overlap = any(is_vert(s) for s in tree.traverse_strokes_point(*l1)) # Vertical touching on the left
			right_overlap = any(is_vert(s) for s in tree.traverse_strokes_point(*r1)) # Vertical touching on the right
			left_block = any(is_block(s) for s in tree.traverse_strokes_point(*l2)) # Hook adjacent on the left
			right_block = any(is_block(s) for s in tree.traverse_strokes_point(*r2)) # Hook adjacent on the right
			left_outside = l2[0] <= 0
			right_outside = r2[0] >= tree.dims[0]
	#		print(left_overlap, right_overlap, left_block, right_block, left_outside, right_outside)
			
			if left_overlap and (not right_block) and (not right_outside):
	#			print('Adjusted right')
				hook.pos = (x+w/2, y)
				hook.dims = (w+w/2, h)
			elif right_overlap and (not left_block) and (not left_outside):
	#			print('Adjusted left')
				hook.pos = (x-w/2, y)
				hook.dims = (w+w/2, h)
		
		return tree

if __name__ == '__main__':
	from parser import parse
	ScadRenderer.render(parse("W[{0[hc]h}v{h[vv2]Mh}v]"), scale=10, margin=1, thickness=2.5).show()

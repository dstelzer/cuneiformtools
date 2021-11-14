import subprocess
from pathlib import Path

import fontforge, psMat
from tqdm import tqdm

from render import *
import parser

class Font:
	def __init__(self, tmpname=Path('tmp.svg'), final_margin=100, initial_margin=100, final_bottom=200, glyph_size=1000, stroke_width=0.025, renderer=TwoSidedRenderer):
		self.font = fontforge.font() # Make a new font
		self.tmp = tmpname
		self.final_margin = final_margin
		self.initial_margin = initial_margin
		self.final_bottom = final_bottom
		self.glyph_size = glyph_size
		self.stroke_width = stroke_width
		self.renderer = renderer
	
	def finalize(self, filename=Path('font.sfd')):
	#	self.font.generate(filename)
		self.font.save(filename)
	
	def select_glyph(self, codepoint):
		self.glyph = self.font.createChar(codepoint)
	
	def inkscape_processing(self):
		actions = [
			'select-all:groups', # Select the main group
			'SelectionUnGroup', # Ungroup it (this is important! without it you get weird tapers)
			'select-all', # Select all the components
			'SelectionBreakApart', # Break the paths down into smaller parts
			'select-all', # Select all the parts
			'object-stroke-to-path', # Convert strokes to outlined paths for the font
			'select-all', # Select all the paths
			'SelectionUnion', # Union them into a single path
			'FileSave', # Save the results
		]
		args = [
			'inkscape',
			'--batch-process', # Allow use of GUI (needed for a couple verbs), but if we do, close it at the end
			'--actions',
			';'.join(actions),
			str(self.tmp), # Both input and output
		]
		subprocess.run(args, stderr=subprocess.DEVNULL)
	
	def read_glyph_data(self):
		self.glyph.importOutlines(str(self.tmp), scale=False)
	#	print(self.glyph.boundingBox())
		x1, y1, x2, y2 = self.glyph.boundingBox()
		dx, dy = x2-x1, y2-y1
		# Goal: y1 = 0, y2 = self.glyph_size, x1 = self.final_margin
		# So first: scale by self.glyph_size / dy
		# This is the size the SVG is rendered at, but FontForge scales things down so the *largest* dimension is no larger than 1000, which means most glyphs don't line up properly
	#	scale = self.glyph_size / dy
	#	self.glyph.transform(psMat.scale(scale, scale))
		# Then recalculate the bounding box (we let FontForge do this for us to avoid rounding errors)
	#	print(self.glyph.boundingBox())
		x1, y1, x2, y2 = self.glyph.boundingBox()
		dx, dy = x2-x1, y2-y1
		# Translate by self.final_margin-x1, -self.final_bottom
		self.glyph.transform(psMat.translate(self.final_margin-x1, self.initial_margin))
		# And finally, set the advance width to dx+2*self.final_margin
		self.glyph.width = round(dx + 2*self.final_margin)
	#	print(self.glyph.boundingBox())
	#	print(self.glyph.width)
		self.glyph.addExtrema()
		self.glyph.autoHint()
	
	def write_glyph_data(self, root):
		data = self.renderer.render(root, scale=self.glyph_size, margin=self.initial_margin, strokewidth=self.stroke_width, fgcolor='black', bgcolor='0', format='svg').get_raw_data() # fgcolor and bgcolor are necessary for the SVG to be read properly
		with open(self.tmp, 'wb') as f: f.write(data.read()) # Transfer the buffer to an actual file because we need Inkscape and FontForge to be able to access it from the command line
	
	def encode_glyph(self, unicode, root):
		if self.font.findEncodingSlot(unicode) != -1: return # Already exists
		self.select_glyph(unicode)
		self.write_glyph_data(root)
		self.inkscape_processing()
		self.read_glyph_data()

def generate_font(renderer):
	from database import Database
	db = Database()
	db.load_data('data/hzl.dat')
	print('Database loaded')
	
	font = Font(renderer=renderer)
	print('Font skeleton prepared')
	
	import csv
	with Path('data/unicode.csv').open('r', newline='') as f:
		r = csv.DictReader(f)
		for row in tqdm(list(r), disable=True):
			hzl = row['HethZL'].strip()
			name = row['Sign Name'].strip()
			tmp = row['Unicode Glyph'].strip()
			if len(tmp.split()) == 2 and tmp.startswith('U+') and hzl: # This is a valid single glyph which has an HZL index
				uni = tmp.split()[0][2:]
				print(f'Looking up sign {hzl}: {name} ({uni})')
				entry = next((e for e in db.data if e.ident==hzl), None)
				if entry is None:
					print(f'Warning: no sign numbered {hzl} found in database! Skipping and moving on')
					continue
				try:
					font.encode_glyph(int(uni, 16), parser.parse(entry.forms[0]))
				except KeyboardInterrupt:
					break
	print('Glyphs encoded')
	
	font.finalize('tmp.sfm')
	print('Font exported! Finished!')

if __name__ == '__main__':
#	f = Font()
#	f.select_glyph(65)
#	f.tmp = Path('/home/daniel/Downloads/tmp/ezen4.svg')
#	f.glyph_import()
#	f.finalize('/home/daniel/Downloads/tmp/tmp.sfd')
	input()
	generate_font(TwoSidedRenderer)

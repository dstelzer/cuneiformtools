import subprocess
from pathlib import Path
import lxml.etree as et

import fontforge, psMat
from tqdm import tqdm

from render import *
import parser

def glyph_name(codepoint): # Give a consistent name to each codepoint
	return f'U{codepoint:04x}'

SANITIZE = { # FontForge doesn't like certain characters in glyph names
	' ' : '_',
	'(' : '',
	')' : '',
	'.' : '_',
	',' : '',
	'/' : '_',
	'Á' : 'A2',
	'À' : 'A3',
	'É' : 'E2',
	'È' : 'E3',
	'Í' : 'I2',
	'Ì' : 'I3',
	'Ú' : 'U2',
	'Ù' : 'U3',
	'Š' : 'C',
	'Ĝ' : 'J',
	'Ḫ' : 'H',
	'Ṭ' : 'T.',
	'Ṣ' : 'S.',
}

def sanitize_name(orig): # Sanitize a name so FontForge doesn't complain
	out = 'LIG_' + orig
	for k,v in SANITIZE.items():
		out = out.replace(k,v)
	print(f'\tSanitized {orig} to {out}')
	return out

ERROR_CODE = parser.parse('*') # A big X in the current renderer's style (since that's the default rendering of a wildcard stroke) - could change to P* to make it narrower if desired

# I HATE that this is necessary
# But recent versions of pycairo export SVGs with stroke, fill, etc as their own element attributes
# Inkscape malfunctions if these are kept separate instead of being put in a single style attribute
# (It seems to work okay but the resulting paths lose their style information, so you'll end up with fills and no strokes)
# So we have to manually go in and fix up the XML
def clean_xml(file1, file2):
	SAFE_ATTRS = {'d', 'transform', 'style'} # The attributes we don't want to change
	tree = et.parse(file1)
#	print('\tRead file')
	for path in tree.getroot().iter():
		if not path.tag.endswith('path'): continue
		if 'style' in path.attrib: continue # Already has a style
		style = []
		iterator = list(path.attrib.items()) # So we can edit while iterating
		for key, val in iterator:
#			print('\t', key, val)
			if key in SAFE_ATTRS: continue
			style.append(f'{key}:{val};')
			del path.attrib[key]
		path.attrib['style'] = ''.join(style)
	tree.write(file2)

class Font:
	def __init__(self, tmpname=Path('font_tmp'), final_margin=100, initial_margin=100, final_bottom=200, glyph_size=1000, stroke_width=0.025, renderer=TwoSidedRenderer, **extra):
		self.font = fontforge.font() # Make a new font
		self.tmp = tmpname
		self.tmp.mkdir(exist_ok=True) # If it doesn't already exist
		self.final_margin = final_margin
		self.initial_margin = initial_margin
		self.final_bottom = final_bottom
		self.glyph_size = glyph_size
		self.stroke_width = stroke_width
		self.renderer = renderer
		
		self.extra = extra
		
		self.used_in_ligatures = set()
		self.used_outside_ligatures = set()
		
		self.make_ligature_tables()
	
	def make_ligature_tables(self):
		self.subtable = 'ligsubtable'
		featuple = ("liga", (("latn","dflt"),("xsux","dflt")) ) # Xsux is script code for cuneiform, but for some reason certain codepoints are assigned to Latn instead
		self.font.addLookup('ligatures', 'gsub_ligature', None, (featuple,))
		self.font.addLookupSubtable('ligatures', self.subtable)
	
	def finalize(self, filename=Path('font.sfd')):
	#	self.font.generate(filename)
		missing = self.used_in_ligatures - self.used_outside_ligatures
		if missing: # If this becomes a problem, put actual handling here
			print('\tWARNING: some signs used in ligatures but not outside them! Encoding as crosses for now...')
			print('\t\t' + ' '.join(f'{c:04x}' for c in missing))
			for cp in missing:
				self.encode_glyph(cp, ERROR_CODE, None) # Creates the missing glyphs but leaves them empty
		self.encode_glyph(0xFFFD, ERROR_CODE, None) # And put the ERROR_CODE symbol at U+FFFD, "replacement character", so that it can be used as an error symbol for font problems later
		self.font.save(filename)
	
	def select_glyph(self, codepoint):
		self.glyph = self.font.createChar(codepoint, glyph_name(codepoint))
		self.used_outside_ligatures.add(codepoint)
	
	def select_ligature(self, cps, name):
		self.glyph = self.font.createChar(-1, sanitize_name(name)) # Make a new character with no Unicode codepoint associated
		self.glyph.addPosSub(self.subtable, tuple(glyph_name(cp) for cp in cps))
		self.used_in_ligatures |= set(cps)
	
	def inkscape_processing(self):
		actions = [
			'select-all:groups', # Select the main group
			'selection-ungroup', # Ungroup it (this is important! without it you get weird tapers)
			'select-all', # Select all the components
			'path-break-apart', # Break the paths down into smaller parts
			'select-all', # Select all the parts
			'object-stroke-to-path', # Convert strokes to outlined paths for the font
			'select-all', # Select all the paths
			'path-union', # Union them into a single path
		]
		args = [
			'inkscape',
			'--batch-process', # Allow use of GUI (needed for a couple verbs), but if we do, close it at the end
			'--actions',
			';'.join(actions),
			'--export-filename=' + str(self.tmp / 'inkscape.svg'), # Output
			str(self.tmp / 'modxml.svg'), # Input
		]
		subprocess.run(args, stderr=subprocess.DEVNULL)
	
	def read_glyph_data(self):
		self.glyph.importOutlines(str(self.tmp / 'inkscape.svg'), scale=False)
	#	print(self.glyph.boundingBox())
	#	x1, y1, x2, y2 = self.glyph.boundingBox()
	#	dx, dy = x2-x1, y2-y1
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
		data = self.renderer.render(root, scale=self.glyph_size, margin=self.initial_margin, fgcolor='black', bgcolor='0', format='svg', **self.extra).get_raw_data() # fgcolor and bgcolor are necessary for the SVG to be read properly
		with open(self.tmp / 'cairo.svg', 'wb') as f: f.write(data.read()) # Transfer the buffer to an actual file because we need Inkscape and FontForge to be able to access it from the command line
		clean_xml(self.tmp / 'cairo.svg', self.tmp / 'modxml.svg')
	
	def encode_glyph(self, unicode, root, name):
		if isinstance(unicode, int): unicode = (unicode,) # Ensure a tuple
		if len(unicode) == 1: # Single codepoint
			if self.font.findEncodingSlot(unicode[0]) != -1: # Already exists
				print(f'\tWarning: codepoint {unicode[0]:04x} already used! Skipping.')
				return # Skip instead of overwriting - if we import another glyph into the slot it'll actually add them together instead of overwriting, and since the first one's already been repositioned, the result will be a mess
			print('\tSelecting single glyph', unicode[0])
			self.select_glyph(unicode[0])
		else: # Ligature of codepoints
			print('\tSelecting ligature', unicode, name)
			self.select_ligature(unicode, name)
		print('\tWriting glyph data')
		self.write_glyph_data(root)
		print('\tProcessing in Inkscape')
		self.inkscape_processing()
		print('\tReading glyph data')
		self.read_glyph_data()

def generate_font(renderer, outname, tags=(), **extra):
	from database import Database
	db = Database()
	db.load_data('data/hzl.dat')
	print('Database loaded')
	
	font = Font(renderer=renderer, **extra)
	print('Font skeleton prepared')
	
	import csv
	with Path('data/unicode_cleaned.csv').open('r', newline='') as f:
		r = csv.DictReader(f)
		for row in r:
			hzl = row['HethZL'].strip()
			if '*' in hzl: # Flags like *B, *C, etc are used when multiple Unicode codepoints should have the same HZL value (due to signs merging in Hittite)
				hzl2 = hzl.split('*')[0]
			else:
				hzl2 = hzl
			name = row['Sign Name'].strip()
			unicode = row['Unicode Glyph'].strip()
			
			if not hzl or not unicode: continue
			codepoints = []
			for c in unicode.split():
				if c.startswith('U+'):
					codepoints.append(int(c[2:], 16)) # Read as hex
			printable = '+'.join(f'{c:04x}' for c in codepoints)
			if not codepoints:
				print(f'\tWarning: no codepoints found for {name} ("{unicode}")')
				continue
			
			print(f'Looking up sign {hzl}: {name} ({printable})')
			entry = next((e for e in db.data if e.ident==hzl2), None)
			if entry is None:
				print(f'\tWarning: no sign numbered {hzl2} found in database! Skipping and moving on')
				continue
			try:
				best = max((f for f in entry.forms), key=lambda f: f.matches(tags)) # Find the form that best matches the tags
				print('\tFound code', best.code)
				font.encode_glyph(codepoints, parser.parse(best.code), name)
			except KeyboardInterrupt:
				break
	print('Glyphs encoded')
	
	font.finalize(outname)
	print('Font exported! Finished!')

if __name__ == '__main__':
#	f = Font()
#	f.select_glyph(65)
#	f.tmp = Path('/home/daniel/Downloads/tmp/ezen4.svg')
#	f.glyph_import()
#	f.finalize('/home/daniel/Downloads/tmp/tmp.sfd')
#	input()
	generate_font(InkRenderer, 'ink.sfd', ('new',), strokewidth=0.05)

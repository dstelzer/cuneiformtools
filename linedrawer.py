#!/usr/bin/env python

from io import BytesIO
import subprocess as sp

import cairo

WIDTH = HEIGHT = 300

# To convert the output from CuneiPainter:
# \{"type":"STROKE","head":\{"x":(\d+),"y":(\d+)\},"tail":\{"x":(\d+),"y":(\d+)\}\},?
# \nmove \1 \2\nline \3 \4

# TODO [{"type":"STROKE","head":{"x":59,"y":52},"tail":{"x":60,"y":265}},{"type":"STROKE","head":{"x":141,"y":206},"tail":{"x":262,"y":204}},{"type":"STROKE","head":{"x":17,"y":90},"tail":{"x":237,"y":91}},{"type":"STROKE","head":{"x":190,"y":50},"tail":{"x":197,"y":258}}]

instructions_all = '''
color 1 1 1 1
blank
color 0 0 0 1
width 1
move 0 0
line 0 300
line 300 300
line 300 0
line 0 0
stroke
'''

instructions_ya = '''
width 5
# the sign YA
move 46 204
line 172 203
move 44 158
line 96 158
move 111 158
line 175 158
move 41 101
line 96 102
move 118 99
line 174 99
move 205 84
line 205 240
move 248 79
line 248 121
move 250 142
line 250 247
stroke

# the projections onto each axis
color 1 0 0 1
width 10
move 0 79
line 0 247
move 41 300
line 175 300
move 200 300
line 210 300
move 243 300
line 255 300
stroke
'''

instructions_lu = '''
width 5
color 1 0 0 1
move 56 34
line 55 263
move 147 33
line 146 263
move 229 29
line 224 264
stroke
color 0 0 1 1
move 13 81
line 265 77
move 14 143
line 280 144
move 15 228
line 272 219
stroke
'''

instructions_imposs = '''
width 5
move 34 69
line 187 66
move 228 33
line 230 217
move 71 109
line 69 264
move 111 237
line 279 241
stroke
'''

instructions_ninda = '''
width 5
move 72 43
line 73 132
move 149 60
line 149 130
move 232 39
line 231 131
move 150 166
line 150 260
stroke
'''

instructions_ninda_sep = '''
color 0 1 0 1
move 50 145
line 250 147
stroke
'''

instructions_tenu = '''
width 5
move 61 108
line 108 197
move 121 78
line 169 167
move 181 41
line 235 134
move 108 270
line 283 162
stroke
'''

instructions_ir = '''
width 5
# upward
color 0 0 1 1
move 35 244
line 258 137
stroke
# downward
color 0 0 0 0.33
move 28 21
line 259 122
stroke
# vertical
color 1 0 0 1
move 71 137
line 71 290
move 140 136
line 141 289
move 201 129
line 201 283
stroke
'''

instructions_p4 = '''
width 5
color 1 0 0 1
move 59 52
line 60 265
stroke
color 0 0 1 1
move 17 90
line 237 91
stroke
color 1 0 0 1
move 190 50
line 197 258
stroke
color 0 0 1 1
move 141 206
line 262 204
stroke
'''

instructions_a = '''
width 5
move 87 44
line 82 255
move 180 41
line 182 127
move 187 133
line 185 248
stroke
color 1 0 0 1
width 10
# Bad tolerance
move 87 300
line 82 300
move 177 300
line 182 300
move 190 300
line 185 300
# Good tolerance
move 80 300
line 90 300
move 175 300
line 195 300
stroke
'''

buffer = BytesIO()
surf = cairo.PDFSurface(buffer, WIDTH, HEIGHT)
ctx = cairo.Context(surf)
ctx.save()

def parse_line(line):
	if not line.strip(): return
	print(line)
	vals = line.strip().split()
	cmd = vals[0].lower()
	vals = vals[1:]
	if cmd == '#':
		return
	elif cmd == 'color':
		ctx.set_source_rgba(*[float(c) for c in vals])
	elif cmd == 'width':
		ctx.set_line_width(float(vals[0]))
	elif cmd == 'blank':
		ctx.rectangle(0, 0, WIDTH, HEIGHT)
		ctx.fill()
	elif cmd == 'move':
		ctx.move_to(*[float(c) for c in vals])
	elif cmd == 'line':
		ctx.line_to(*[float(c) for c in vals])
	elif cmd == 'stroke':
		ctx.stroke()
	else:
		raise ValueError(cmd)

for line in (instructions_all+instructions_a).split('\n'):
	parse_line(line)

surf.show_page()
surf.finish()
with open('tmp.pdf', 'wb') as f:
	f.write(buffer.getvalue())
print('Done')
sp.run(['xdg-open', 'tmp.pdf'])

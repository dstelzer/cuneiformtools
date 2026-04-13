#!/usr/bin/env python3

from render import *
from render3d import *
from parser import parse, parse_sequence
from layout import Layout
from database import Database

def test_rendering():
	while True:
	#	try:
			construct = parse(input('>') or 'S([0\'"v!]h2)', friendly=True)
			print(construct)
			print(construct.functional_form())
			print(construct.forest())
			InkRenderer.render(construct, scale=256, margin=19.2, strokewidth=0.05, format='pdf', bgcolor='white', fgcolor='black', ).show()
		#	TwoSidedRenderer.render(construct, margin=32).show()
		#	TwoSidedRenderer.render(construct, ('1')).show()
		#	TwoSidedRenderer.render(construct.functional_form()).show()
	#	except ValueError: pass

def test_group_rendering():
	while True:
		try:
			seq = parse_sequence(input())
			SharpInkRenderer.render_sequence(seq, justify='c').show()
		except ValueError: pass

def test_comparisons():
	while True:
		outer = parse(input('Outer: '))
		outf = outer.functional_form()
		print(outf)
		inner = parse(input('Inner: '))
		inf = inner.functional_form()
		print(inf)
		if inf in outf:
			match = outf.highlight_containment(inf)
	#		print(match)
			print('Match:', match)
			TwoSidedRenderer.render(outer, match).show()
		else:
			print('No match')
		print()

def test_layout():
	db = Database()
	db.load_cleanup('data/cleanup.dat')
	db.load_expansions('data/replacements.dat')
	db.load_data('data/hzl.dat')
	db.prepare_sorting()
	while True:
		desc = input()
		if not desc: desc = 'nu NINDA-an e-ez-za-at-te-ni/3 `n wa-a-tar-ma e-ku-ut-te-ni/3 `r nu NINDA-an `F'
		Layout(InkRenderer, justify='s', size=256, margin=0.25).render(db.parse_transcription(desc), strokewidth=0.05).show()
	#	Layout(ScadRenderer, justify='s', size=15, margin=0.25).render(db.parse_transcription(desc), fill=True, thickness=5, shape='seal').show()
	#	Layout(ScadRenderer, justify='s', size=10, margin=0.25).render(db.parse_transcription(desc), fill=True, thickness=5, shape='tablet').show()

def test_seals():
	db = Database()
	db.load_cleanup('data/cleanup.dat')
	db.load_expansions('data/replacements.dat')
	db.load_data('data/hzl.dat')
	db.prepare_sorting()
	while True:
		desc = input()
		if not desc: desc = 'nu NINDA-an e-ez-za-at-te-ni/3 `n wa-a-tar-ma e-ku-ut-te-ni/3 `r nu NINDA-an `F'
		Layout(ScadRenderer, justify='s', size=10, margin=0.25).render(db.parse_transcription(desc, ('new',)), fill=True, thickness=-5, shape='seal', multiplex=3, extramargin=5).show()
		# Size should be 10 or 15, both work well atm
		# Thickness should be 1.5 or negative
		# Cookie cutter: nu NINDA-an `n ez-za-te-%{d([vv0]u)}
		# New version:   nu NINDA-an `n ez-za-%W[{hh}{hhhh}v0'"{[vv]v}TEE]
		# 		(That last sign is AT + TÉN combined to fit nicely)
		# Ea-Nāṣir: ana2-É.A `n na-ṣi-%{d([vvv]u)} `n qí-bí-ma
		# Dog: %{[vvhv]Ah}-%P[{hh'h'h'h}v]-%[(h[vv{0c}])v]-%P[{h'h'h'h}v]-%[{cc}v'"{du}v]-%P[{hh'h}v]-%[{0hh0}{u0d}v] `n %[{[cc]h[cc]}{cc}]-%L[{hh'h'h'h}v2(h[v'"v'"v'"])EEv2]-%[{h(h[vvv])Mh}v]-%[{h0([0vv0EE]h)}v]-%[{h0([0vv0EE]h)}v] `n %(hu'")-%[{ud}v'{du}]-%[{h(h[vvv])Mh}v]-%P[vv2]-%(hvd'"u'")
		# Scribes: inim-inim-ma-nam-dumu `n é-dub-ba-a-ke4-ne `n cu-za-íb-ci-in-tùm
		# Rearranged: %[{0[hc]h}v(v{0hh})]-%[{0[hc]h}v(v{0hh})]-%[{hhh}v]-nam `n %{[{hhh}{hh}]E([0v]h)}-%L[{hh}Evv'v'v'v]-%P[{hh}{hh}v]-%P[{hh'd}v]-a `n %[{0hh}vv'v]-%L[{hh}{[vvv]v}TEE{hh}v]-cu-za `n %[{chh}{h'h'h'h}]-ci-%[{ccc}{ccc}{du}]-%L[c'{d[{h'h[vvv0]}v0]u}c"v]
	#	Layout(ScadRenderer, justify='s', size=10, margin=0.25).render(db.parse_transcription(desc, ('new',)), fill=True, thickness=5, shape='tablet').show()
		# f-e-%[{h[hc]h}v] %[{[hc']h}vv]-te-el-%[{[hc']([hc']v)R}v]-ar `n MUNUS.TÚG mi-nu-ú-ti-im
# cylindrify(132.0, 41, 5, 50*($preview?1:10))

def test_uga():
	db = Database()
	db.load_data('data/uga.dat')
	db.prepare_sorting()
	while True:
		desc = input()
		Layout(TwoSidedRenderer, justify='l', spacing=0.67).render(db.parse_transcription(desc), fill=True).show()

def test_normalization():
	basic = parse('{h([vv]h)}')
	print('First:', end=' ')
	for s in basic.traverse_strokes():
		print(f'{s._sigil()}{s.ident}', end=' ')
	print()
	normal = basic.functional_form()
	print('Second:', end=' ')
	for s in normal.traverse_strokes():
		print(f'{s._sigil()}{s.ident}', end=' ')
	print()

def regression_testing():
	with open('regression.in', 'r') as f1:
		with open('regression.out', 'w') as f2:
			for line in f1:
				print('.', end='', flush=True)
				construct = parse(line.strip())
				func = construct.functional_form()
				f2.write(str(func)+'\n')
	print('Done')

if __name__ == '__main__':
	test_seals()

# Test case for stack containment: Outer: [v{h[{cc}{cc}]h}v] Inner: {h[cc][cc]h}
# Make sure it also matches [{cc}{cc}]

# Crash comes from {h[0{cc}{hh}{hh}0]h} - FIXED

# CRASH TO FIX
# {h[vT]M} causes an infinite loop
# Search for PASS_LIMIT in elements.py to see where
# Currently added a way to break out of it if there's trouble
# But this deserves more attention!

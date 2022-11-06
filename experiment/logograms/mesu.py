# Mesû = clean up

import hantatallas.database as database

db = database.Database()
db.load_data('hantatallas/data/hzl.dat')
db.load_expansions('hantatallas/data/replacements.dat')
db.load_cleanup('hantatallas/data/cleanup.dat')

DAMAGE_MARKERS = {'⸢', '⸣', '[', ']'}

def get_phonograms(glyph):
	glyph = db.clean_name(glyph)
	if glyph not in db.name_lookup:
		print(f'Warning: glyph {glyph} not known')
		return None
		#raise ValueError(f'Glyph {glyph} not known')
	entry = db.name_lookup[glyph]
	return ', '.join(entry.langs['HIT'])

def explain_tablet(tab):
	trans = str.maketrans('', '', ''.join(DAMAGE_MARKERS)) # Translation table to remove damage markers
	broken = set()
	intact = set()
	phon = set()
	unk = set()
	for glyph in tab.glyphs:
		glyph = glyph.strip()
		if not glyph: continue
		b = any(d in glyph for d in DAMAGE_MARKERS) # Is it damaged?
		alt = glyph.translate(trans) # Alternate form without any damage markers in it
		if not alt: continue
		ph = get_phonograms(alt)
		
		if ph is None: # Not found
			unk.add(glyph)
		elif ph:
			phon.add(f'{glyph} ({ph})')
		elif b:
			broken.add(glyph)
		else:
			intact.add(glyph)
	
	return f'''<h3>{' '.join(str(x) for x in tab.ident)}</h3>
	<p><b>Intact:</b> {', '.join(sorted(intact))}</p>
	<p><b>Damaged:</b> {', '.join(sorted(broken))}</p>
	<p><b>Simple:</b> {', '.join(sorted(phon))}</p>
	<p><b>Unknown:</b> {', '.join(sorted(unk))}</p>'''

def explain_collection(coll):
	lines = []
	for tab in coll.tablets.values():
		lines.append(explain_tablet(tab))
	return '\n\n'.join(lines)

def write_collection(coll, fn, title='Collection'):
	with open(fn, 'w') as f:
		f.write(f'''<html>
<head><title>{title}</title></head>
<body>
{explain_collection(coll)}
</body>
</html>''')

if __name__ == '__main__':
	from zaru import Collection
	coll = Collection.from_file('glyphs_1.pickle')
	write_collection(coll, 'overview_1.html', '1')

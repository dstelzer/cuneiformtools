# Ettuttu = "spider" in Akkadian (written AŠ₅)

import pickle

from bs4 import BeautifulSoup
import requests
from tqdm import tqdm

ACCEPTABLE_VOLUMES = set(range(23, 44)) # Which volumes does the library have?
CORE_URL = 'https://www.hethport.uni-wuerzburg.de/HFR/bascorp_idx1.php'
BASE_URL = 'https://www.hethport.uni-wuerzburg.de/HFR/'

def request_and_parse(url):
	resp = requests.get(url)
	resp.raise_for_status()
	soup = BeautifulSoup(resp.text, 'lxml')
	return soup

def h4_before_h6(node):
	return node.name == 'h4' and bool(node.find_next_siblings('h6'))

def int_clean(s): # Remove any letters from right edge
	while s[-1] not in '1234567890': s = s[:-1]
	return int(s)

def is_logogram_class(cls):
	return cls in {'sGr', 'd'}

left_brackets = {'⸢', '['}
right_brackets = {'⸣', ']'}
all_brackets = left_brackets | right_brackets

def glyphs_from(node): # Split the contents of a node into a series of dot-delimited logograms (and also include brackets or half-brackets if they were left just outside that node - we want to know about damage!)
	text = ''.join(node.stripped_strings)
	
	prev = node.find_previous_sibling(name='span')
	if prev and 'del' in prev.get('class', ()) and any(c in prev.string for c in left_brackets): # .get(x, ()) returns an empty tuple if the element has no class, which happens very rarely but *can* happen
		text = prev.string.strip() + text
	
	nxt = node.find_next_sibling(name='span')
	if nxt and 'del' in nxt.get('class', ()) and any(c in nxt.string for c in right_brackets):
		text = text + nxt.string.strip()
	
	glyphs = text.split('.')
	return set(glyphs)

def extract_text(soup):
	h4 = soup.find_all(h4_before_h6) # h4 whose sibling is an h6 - should match only the name tag
	if len(h4) != 1: #raise ValueError('Could not find unique h6~h4', h4)
		print(f'WARNING: Found {len(main)} h6~h4s. Continue?')
	main = soup.find_all('div', class_='XXXlang')
	if len(main) != 1: #raise ValueError('Could not find unique XXXlang', main)
		print(f'WARNING: Found {len(main)} XXXlangs. Taking only the first.')
	text = str(h4[0]) + '\n' + str(main[0])
	
	glyphs = set()
	logograms = soup.find_all(name='span', class_=is_logogram_class) # Spans of class sGr or d (sumerogram or determinative)
	# TODO: include akkadograms?
	for l in logograms:
		glyphs |= glyphs_from(l)
	
	key = str(h4[0].string).split()
	work = key[0]
	if work != 'KBo': #raise ValueError('Not from KBo', key)
		print('WARNING: No KBo identification found. Discarding.')
		return None
	try:
		vol, tab = key[1].split('.')
		vol = int(vol)
		tab = int_clean(tab)
	except ValueError:
		print(key)
		raise
	return ((work, vol, tab), text, glyphs)

def iterate_tablets(soup):
	for link in soup.select('ol li h6 a'): # Find the links to tablets
		key = str(link.string).split()
		multi = '+' in str(link.string)
		work = key[0]
		if work == 'KBo' and not multi: # This tablet is in KBo and is not a compilation of multiple tablets
			vol = int(key[1].split('.')[0])
			if vol in ACCEPTABLE_VOLUMES: # And specifically in a volume I have access to through the library
				yield link['href']

def iterate_indirectly(soup):
	data = soup.select('ul li h6 a')
	for i, link in enumerate(tqdm(data)):
		name = link.get_text()
		href = link['href']
	#	print(f'Parsing {name} ({i+1}/{len(data)})...')
		soup = request_and_parse(BASE_URL+href)
		yield from iterate_tablets(soup)

def anchor(index): return f'{index[0]}.{index[1]}.{index[2]}'

def do_the_thing():
	print('Getting initial list')
	soup = request_and_parse(CORE_URL)
	
	print('Gathering data')
	texts = {}
	glyphsets = {}
	for href in iterate_indirectly(soup):
		try:
			res = extract_text(request_and_parse(BASE_URL+href))
			if res is None: continue
			index, text, glyphs = res
	#		print(f'\tFound tablet {index[1]}.{index[2]}')
			texts[index] = text
			glyphsets[index] = glyphs
		except:
			print(f'!! Error in url {BASE_URL+href}')
			raise
	
	def list_element(index):
		target = anchor(index)
		name = f'{index[0]} {index[1]}.{index[2]}'
		return f'<li><a href="#{target}">{name}</a></li>\n'
	
	def writeup(index, text):
		return f'<hr /><p class="entry"><a name="{anchor(index)}"></a>\n{text}\n</p>\n'
	
	print('Writing glyphs')
	with open('glyphs.pickle', 'wb') as f:
		pickle.dump(glyphsets, f)
	input('(Stop now?)')
	
	print('Writing results')
	volumes = sorted(set(index[1] for index in texts.keys()))
	for vol in tqdm(volumes):
		header = f'<html><head><link rel="stylesheet" href="custom.css" /><link rel="stylesheet" href="ttp3.css" /><title>Volume {vol}</title></head><body><ul>\n'
		midbar = '</ul>\n'
		footer = '\n\n</body></html>'
		
		page = (header
			+ '\n'.join(list_element(index) for index in sorted(texts.keys()) if index[1]==vol)
			+ midbar
			+ '\n'.join(writeup(index, text) for index, text in sorted(texts.items()) if index[1]==vol)
			+ footer)
		
		with open(f'volume_{vol}.html', 'w') as f:
			f.write(page)
	
	print('Writing index')
	page = '<html><head><title>Index</title></head><body><ul>' + '\n'.join(f'<li><a href="volume_{vol}.html">Volume {vol}</a></li>' for vol in volumes) + '</ul></body></html>'
	with open('index.html', 'w') as f:
		f.write(page)
	
	print('Done!')

def test_glyphing(url):
	index, text, glyphs = extract_text(request_and_parse(url))
	print(index)
	print(text[:30])
	print(glyphs)

if __name__ == '__main__':
	input()
#	test_glyphing('https://www.hethport.uni-wuerzburg.de/HFR/bascorp_xtx.php?d=KUB%2029.4%2B&o=CTH%20481')
	do_the_thing()

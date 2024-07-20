from pathlib import Path

from .render import *
from .parser import parse, parse_sequence
from .database import Database

# This file exposes easy access to various Hantatallas features, so that they can be used when testing other components. It shouldn't be used in production since it's extremely inflexible.

def render(s):
	TwoSidedRenderer.render(parse(s, friendly=True)).show()

db = None

def prepare_lookup():
	global db
	db = Database()
	data = Path(__file__).parent / 'data'
	db.load_cleanup(data / 'cleanup.dat')
	db.load_expansions(data / 'replacements.dat')
	db.load_data(data / 'hzl.dat')
	db.prepare_sorting()

def hack_name(e):
	for lang in ['HIT', 'HURR', 'AKK', 'SUM', 'DET']:
		if e.langs[lang]: return e.langs[lang][0]
	return e.ident

def lookup(s):
	if db is None: prepare_lookup()
	form = parse(s, friendly=True).functional_form()
	print('This could be ', end='')
	for entry in db.sorted['complex']:
		if list(entry.find_matches(form, '')):
			print(hack_name(entry), end=' ')
			break
	print()

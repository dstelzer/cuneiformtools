from contextlib import redirect_stdout
from io import StringIO, BytesIO
from urllib.parse import urlencode
import html
import re

from flask import Response
from werkzeug.wsgi import FileWrapper

from .render import *
from .parser import parse, parse_sequence
from .database import Database
from .layout import Layout

renderers = {
	'publish' : TwoSidedRenderer,
	'handwrite' : OneSidedRenderer,
	'linear' : LinearRenderer,
	'triangle' : TriangleRenderer,
}

def formatted_response(data, format):
	if format not in ('png', 'svg', 'pdf'): return f'<pre>Unrecognized format "{format}"</pre>' # Safety check
	if format == 'png': mime = 'image/png'
	elif format == 'svg': mime = 'image/svg+xml'
	elif format == 'pdf': mime = 'application/pdf'
	w = FileWrapper(data)
	return Response(w, mimetype=mime, direct_passthrough=True)

def do_rendering(instr, rendname, highlight='', format='png', friendly=False, sequence=False, *args, **kwargs):
	log = StringIO() # If there's an error, it'll get pretty-printed to stdout. So we capture everything sent to stdout in order to show it to the user if needed.
	try:
		with redirect_stdout(log):
			func = parse_sequence if sequence else parse
			output = func(instr, friendly=friendly)
	except ValueError:
		return '<pre>'+log.getvalue()+'</pre>'
	
	if highlight: hl = highlight.split(',')
	else: hl = ()
	
	rend = renderers[rendname]
	func = rend.render_sequence if sequence else rend.render # Choose the right rendering function to invoke
	data = func(output, hl, format=format, *args, **kwargs).get_raw_data()
	
	return formatted_response(data, format)

def make_image(code, match=()):
	raw = {'text':code, 'type':'publish'}
	if match: raw['highlight'] = ','.join(str(s) for s in match)
	query = urlencode(raw)
	return f'<img src="/rendersign?{query}" height="100px" />'

db = Database()
db.load_cleanup('./hantatallas/data/cleanup.dat')
db.load_expansions('./hantatallas/data/replacements.dat')
db.load_data('./hantatallas/data/hzl.dat')
db.prepare_sorting()

def do_searching(code, regex, sort):
	log = StringIO()
	if code.strip():
		try:
			with redirect_stdout(log):
				piece = parse(code)
		except ValueError:
			return -1, '<pre>'+log.getvalue()+'</pre>'
	else:
		piece = None
	
	if regex.strip():
		try:
			recomp = re.compile(regex.strip())
		except re.error as e:
			return -1, f'<pre>Regex error: {e.args[0]}</pre>'
	else:
		recomp = None
	
	return db.lookup_as_table(piece, recomp, sort)

def do_scribing(instr, rendname, format='png', rendparams=None, layoutparams=None):
	log = StringIO() # If there's an error, it'll get pretty-printed to stdout. So we capture everything sent to stdout in order to show it to the user if needed.
	try:
		with redirect_stdout(log):
			rows = db.parse_transcription(instr)
	except ValueError as e:
		result = log.getvalue() or 'Error outside normal handling system\n'+'\n'.join(e.args) # The error message should always be pretty-printed to stdout, but just in case it's not we have a fallback here (printing the exception's arguments)
		return '<pre>'+result+'</pre>'
	
	renderclass = renderers[rendname]
	
	data = Layout(renderclass=renderclass, **layoutparams).render(rows, format=format, **rendparams).get_raw_data()
	
	return formatted_response(data, format)

from contextlib import redirect_stdout
from io import StringIO, BytesIO
from urllib.parse import urlencode
import html

from flask import Response
from werkzeug.wsgi import FileWrapper

from .render import *
from .parser import parse, parse_sequence
from .database import Database

renderers = {
	'publish' : TwoSidedRenderer,
	'handwrite' : OneSidedRenderer,
	'linear' : LinearRenderer,
}

def do_rendering(instr, rendname, highlight='', format='png', friendly=False, sequence=False, *args, **kwargs):
	if format not in ('png', 'svg', 'pdf'): return f'Unrecognized format {format}' # Safety check
	
	log = StringIO()
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
	w = FileWrapper(data)
	
	if format == 'png': mime = 'image/png'
	elif format == 'svg': mime = 'image/svg+xml'
	elif format == 'pdf': mime = 'application/pdf'
	
	return Response(w, mimetype=mime, direct_passthrough=True)

def make_image(code, match=()):
	raw = {'text':code, 'type':'publish'}
	if match: raw['highlight'] = ','.join(str(s) for s in match)
	query = urlencode(raw)
	return f'<img src="/rendersign?{query}" height="100px" />'

db = Database()
db.load_data('./hantatallas/data/hzl.dat')
db.prepare_sorting()

def do_searching(code, sort):
	log = StringIO()
	try:
		with redirect_stdout(log):
			piece = parse(code)
	except ValueError:
		return -1, '<pre>'+log.getvalue()+'</pre>'
	return db.lookup_as_table(piece, sort)

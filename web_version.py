from contextlib import redirect_stdout
from io import StringIO, BytesIO
from urllib.parse import urlencode
import html

from flask import Response
from werkzeug.wsgi import FileWrapper

from .render import *
from .parser import parse
from .database2 import Database

renderers = {
	'publish' : TwoSidedRenderer,
	'handwrite' : OneSidedRenderer,
	'linear' : LinearRenderer,
}

def do_rendering(instr, rendname, highlight='', format='png', friendly=False):
	if format not in ('png', 'svg'): return 'Invalid format' # Safety check
	
	log = StringIO()
	try:
		with redirect_stdout(log):
			output = parse(instr, friendly)
	except ValueError:
		return '<pre>'+log.getvalue()+'</pre>'
	
	if highlight: hl = highlight.split(',')
	else: hl = ()
	
	rend = renderers[rendname]
	data = rend.render(output, hl, format=format).get_raw_data()
	w = FileWrapper(data)
	
	if format == 'png': mime = 'image/png'
	elif format == 'svg': mime = 'image/svg+xml'
	
	return Response(w, mimetype=mime, direct_passthrough=True)

def make_image(code, match=()):
	raw = {'text':code, 'type':'publish'}
	if match: raw['highlight'] = ','.join(str(s) for s in match)
	query = urlencode(raw)
	return f'<img src="/hantatallas_process?{query}" height="100px" />'

db = Database()
db.load_file('./hantatallas/data/work.txt')
db.prepare_sorting()

def do_searching(code, sort):
	log = StringIO()
	try:
		with redirect_stdout(log):
			piece = parse(code)
	except ValueError:
		return '<pre>'+log.getvalue()+'</pre>'
	table = db.lookup_as_table(piece, sort)
	img = make_image(code)
	form = '''<form action="/hantatallas_search" method="get" accept-charset="utf-8">
			<input type="text" name="code" size="20" value="" />
			<label>Sort by: <select name="sort">
				<option value="hzl">HZL number</option>
				<option value="complex">Complexity</option>
				<option value="usage">Usage</option>
			</select></label>
			<input type="submit" value="Search" />
		</form>'''
	return f'''<html><head>
				<title>Results</title>
				<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
				<style>
					table, th, td {{
						border: 1px solid black;
						border-collapse: collapse;
					}}
					th {{
						background-color: #AAAAAA;
						position: sticky;
						z-index: 100;
						left: 0;
					}}
				</style>
			</head><body>
				<h2>Signs containing <tt>{code}</tt></h2>
				<p>{img} {form}</p>
				<p>{table}</p>
			</body></html>'''

from contextlib import redirect_stdout
from io import StringIO, BytesIO

from flask import Response
from werkzeug.wsgi import FileWrapper

from .render import *
from .parser import parse

renderers = {
	'publish' : TwoSidedRenderer,
	'handwrite' : OneSidedRenderer,
	'linear' : LinearRenderer,
}

def do_the_thing(instr, rendname):
	log = StringIO()
	try:
		with redirect_stdout(log):
			output = parse(instr)
	except ValueError:
		return '<pre>'+log.getvalue()+'</pre>'
	img = BytesIO()
	rend = renderers[rendname]
	data = rend.render(output)
	data.surf.write_to_png(img)
	img.seek(0)
	w = FileWrapper(img)
	return Response(w, mimetype='image/png', direct_passthrough=True)

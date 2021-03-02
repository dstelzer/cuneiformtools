from io import BytesIO

from flask import Flask, request, Response, render_template
from werkzeug.wsgi import FileWrapper

from dubsar.consolidated import DubSar
from hantatallas.web_version import do_rendering, do_searching

app = Flask(__name__)

@app.route('/dubsar_process')
def do_dubsar():
	text = request.args.get('text', '', type=str)
	scale = request.args.get('scale', False, type=bool)
	bg = request.args.get('bg', False, type=bool)
	img = DubSar.do_it_all(text, rescale=scale, bg=bg)
	
	io = BytesIO()
	img.save(io, 'PNG')
	io.seek(0)
	w = FileWrapper(io)
	return Response(w, mimetype='image/png', direct_passthrough=True)

@app.route('/rendersign')
def do_hantatallas():
	text = request.args.get('code', '', type=str)
	rend = request.args.get('type', 'publish', type=str)
	hlight = request.args.get('highlight', '', type=str)
	format = request.args.get('format', 'png', type=str)
	friendly = request.args.get('friendly', 0, type=int)
	bgcolor = request.args.get('bgcolor', None, type=str)
	fgcolor = request.args.get('fgcolor', None, type=str)
	hlcolor = request.args.get('hlcolor', None, type=str)
	scale = request.args.get('scale', 512, type=int)
	margin = request.args.get('margin', 32, type=int)
	return do_rendering(text, rendname=rend, highlight=hlight, format=format, friendly=friendly, bgcolor=bgcolor, fgcolor=fgcolor, hlcolor=hlcolor, scale=scale, margin=margin)

@app.route('/search')
def do_hant_search():
	code = request.args.get('code', '', type=str)
	sort = request.args.get('sort', 'hzl', type=str)
	matches, table = do_searching(code, sort)
	return render_template('search.html', code=code, sort=sort, matches=matches, table=table)

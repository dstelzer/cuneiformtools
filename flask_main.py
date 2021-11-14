from io import BytesIO

from flask import Flask, request, Response, render_template
from werkzeug.wsgi import FileWrapper

from dubsar.consolidated import DubSar
from hantatallas.web_version import do_rendering, do_searching, do_scribing

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

@app.route('/rendersign', methods=['GET','POST'])
def do_hantatallas():
	# We need to get the params in a slightly different way depending on the request method
	# But GET is extremely convenient for image embedding and POST can circumvent the 2048-character limit for longer texts
	# So we support both
	if request.method == 'GET': args = request.args
	elif request.method == 'POST': args = request.form
	
	text = args.get('code', '', type=str)
	rend = args.get('type', 'publish', type=str)
	hlight = args.get('highlight', '', type=str)
	format = args.get('format', 'png', type=str)
	friendly = args.get('friendly', 0, type=int)
	bgcolor = args.get('bgcolor', None, type=str)
	fgcolor = args.get('fgcolor', None, type=str)
	hlcolor = args.get('hlcolor', None, type=str)
	strokewidth = args.get('strokewidth', None, type=float)
	fill = args.get('fill', 0, type=int)
	scale = args.get('scale', 512, type=int)
	margin = args.get('margin', 32, type=int)
	seq = args.get('sequence', 0, type=int)
	just = args.get('justify', 'c', type=str)
	return do_rendering(text, rendname=rend, highlight=hlight, format=format, friendly=friendly, bgcolor=bgcolor, fgcolor=fgcolor, hlcolor=hlcolor, strokewidth=strokewidth, fill=fill, scale=scale, margin=margin, sequence=seq, justify=just)

@app.route('/search')
def do_hant_search():
	code = request.args.get('code', '', type=str)
	regex = request.args.get('regex', '', type=str)
	sort = request.args.get('sort', 'hzl', type=str)
	matches, table = do_searching(code, regex, sort)
	return render_template('search.html', code=code, regex=regex, sort=sort, matches=matches, table=table)

@app.route('/galdubsar', methods=['GET', 'POST'])
def do_galdubsar():
	# As above re GET/POST
	if request.method == 'GET': args = request.args
	elif request.method == 'POST': args = request.form
	
	text = args.get('code', '', type=str)
	rend = args.get('type', 'publish', type=str)
	format = args.get('format', 'png', type=str)
	bgcolor = args.get('bgcolor', None, type=str)
	fgcolor = args.get('fgcolor', None, type=str)
	hlcolor = args.get('hlcolor', None, type=str)
	strokewidth = args.get('strokewidth', None, type=float)
	hatchspace = args.get('hatchspace', None, type=float)
	fill = args.get('fill', 0, type=int)
	justify = args.get('justify', 'l', type=str)
	size = args.get('size', 256, type=int)
	margin = args.get('margin', 1/8, type=float)
	leading = args.get('leading', 1/4, type=float)
	spacing = args.get('spacing', 1/2, type=float)
	kerning = args.get('kerning', 1/8, type=float)
	absolute = args.get('absolute', 0, type=int)
	fixedwidth = args.get('fixedwidth', 0, type=float)
	
	rendparams = {'bgcolor':bgcolor, 'fgcolor':fgcolor, 'hlcolor':hlcolor, 'strokewidth':strokewidth, 'hatchspace':hatchspace, 'fill':fill}
	layoutparams = {'justify':justify, 'size':size, 'margin':margin, 'leading':leading, 'spacing':spacing, 'kerning':kerning, 'absolute':absolute, 'fixed':fixedwidth}
	return do_scribing(text, rendname=rend, format=format, rendparams=rendparams, layoutparams=layoutparams)

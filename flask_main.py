from io import BytesIO

from flask import Flask, request, Response, render_template, send_file, redirect, url_for
from werkzeug.wsgi import FileWrapper

from dubsar.consolidated import DubSar
from hantatallas.web_version import do_rendering, do_searching, do_scribing
from hantatallas.experiment import choose_image, record_stimulus, record_response, record_survey

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
	expkey = request.args.get('expkey', '', type=str)
	matches, table = do_searching(code, regex, sort, expkey=expkey)
	return render_template('search.html', code=code, regex=regex, sort=sort, matches=matches, table=table, expkey=expkey)

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

@app.route('/experiment/image')
def do_experiment_image():
	expkey = request.args.get('expkey', '', type=str)
	index = request.args.get('index', 0, type=int)
	lst = request.args.get('list', '', type=str)
	fn = choose_image(subject=expkey, index=index, lst=lst)
	return send_file(fn, mimetype='image/png')
@app.route('/experiment/respond')
def do_experiment_submit():
	expkey = request.args.get('expkey', '', type=str)
	index = request.args.get('index', -1, type=int)
	lst = request.args.get('list', '', type=str)
	result = request.args.get('result', '', type=str)
	system = request.args.get('system', None, type=str)
	record_response(expkey, index, lst, system, result)
	return redirect(url_for('.do_experiment_stimulus', expkey=expkey, index=index+1, lst=lst, system=system))
@app.route('/experiment/stimulus')
def do_experiment_stimulus():
	total = 16
	expkey = request.args.get('expkey', '', type=str)
	index = request.args.get('index', -1, type=int)
	lst = request.args.get('list', '', type=str)
	system = request.args.get('system', None, type=str)
	if index == total:
		return redirect(url_for('.do_experiment_give_survey', expkey=expkey, which='final', system=system))
	record_stimulus(expkey, index, lst, system)
	return render_template('stimulus.html', expkey=expkey, index=index, lst=lst, system=system, total=total)
@app.route('/experiment/cover')
def do_experiment_cover():
	expkey = request.args.get('expkey', '', type=str)
	index = request.args.get('index', -1, type=int)
	lst = request.args.get('list', '', type=str)
	system = request.args.get('system', None, type=str)
	return render_template('cover.html', expkey=expkey, index=index, lst=lst, system=system)
@app.route('/experiment/survey')
def do_experiment_survey():
	expkey = request.args.get('expkey', '', type=str)
	rest = request.args.to_dict()
	record_survey(expkey, rest)
	return redirect('/experiment/complete.html')
@app.route('/experiment/give_survey')
def do_experiment_give_survey():
	expkey = request.args.get('expkey', '', type=str)
	which = request.args.get('which', '', type=str)
	system = request.args.get('system', None, type=str)
	return render_template('survey.html', expkey=expkey, which=which, system=system)

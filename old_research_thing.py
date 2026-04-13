@app.route('/research_survey')
def do_research_survey():
	from listmaker import make_list
	which = request.args.get('which', '', type=str)
	return make_list(which)

@app.route('/submit_survey', methods=['POST'])
def do_submit_survey():
	import json
	data = dict(request.form)
	with open('tmp_survey.json', 'r') as f:
		full = json.load(f)
	full.append(data)
	with open('tmp_survey.json', 'w') as f:
		json.dump(full, f)
	return f'Data submitted successfully! We now have {len(full)} data points. Thank you!'

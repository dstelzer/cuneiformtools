import csv
from datetime import datetime
import json
from collections import defaultdict

from tqdm import tqdm

FORMAT = '%Y-%m-%d %H:%M:%S,%f'

def process_results(inf, outf, chosen=None):
	starts = {}
	ends = {}
	data = {}
	
	def makekey(subject, payload): # A tuple of just enough information from the payload to ensure uniqueness - `list` and `index` should be enough (or just `name` on its own, if we assume I didn't make any mistakes in arranging the lists), but we include `system` as well just to be sure
		return subject, payload['system'], payload['list'], payload['index']
	
	with open(inf, 'r', newline='') as f:
		reader = csv.reader(f)
		for line in tqdm(reader):
			stamp, subject, action, payload = line
			payload = json.loads(payload)
			stamp = datetime.strptime(stamp, FORMAT)
		#	stamp = datetime.fromisoformat(stamp)
			if action == 'STIMULUS':
				key = makekey(subject, payload)
				starts[key] = stamp
				data[key] = payload
			elif action == 'RESPONSE':
				key = makekey(subject, payload)
				ends[key] = stamp
				data[key].update(payload)
	
	with open(outf, 'w', newline='') as f:
		writer = csv.writer(f)
		writer.writerow(('Subject', 'Duration', 'System', 'List', 'Index', 'Which', 'Name', 'Result', 'Accuracy'))
		
		for key in tqdm(ends.keys()):
			subject = key[0]
			if chosen is None or subject in chosen:
				duration = (ends[key] - starts[key]).total_seconds()
				payload = data[key]
				
				row = (
					subject,
					duration,
					payload['system'],
					payload['list'],
					payload['index'],
					payload['which'],
					payload['name'],
					payload['result'],
				)
				
				writer.writerow(row)

def process_surveys(inf, outf, filter=None):
	qs_init = {
		'current':'Currently enrolled in Hittite',
		'semesters':'Semesters taken (including current)',
		'outside':'Outside experience',
		'cv':'Familiarity with V, CV, VC',
		'cvc':'Familiarity with CVC',
		'logo':'Familiarity with logograms',
		'hzl':'Familiarity with the Zeichenlexikon',
		'hantatallas':'Familiarity with Hantatallas',
		'german':'Can read German',
		'other':'Other information',
	}
	qs_final = {
		'difficulty':'Difficult to use',
		'tiring':'Tiring to use',
		'certainty':'Certain of answers',
		'easiest':'Easiest aspects',
		'worst':'Worst aspects',
		'improve':'Suggested improvements',
		'other':'Other information',
	}
	
	data = defaultdict(dict)
	
	with open(inf, 'r', newline='') as f:
		reader = csv.reader(f)
		for line in tqdm(reader):
			stamp, subject, action, payload = line
			payload = json.loads(payload)
			if filter and subject not in filter: continue
			
			if action == 'SURVEY':
				if payload['which'] == 'initial':
					key = 'I'
				elif payload['which'] == 'final' and payload['system'] == 'H':
					key = 'H'
				elif payload['which'] == 'final' and payload['system'] == 'Z':
					key = 'Z'
				else: # We could just say if not initial, then key = system, but this allows us to be more thorough in detecting mistakes
					raise ValueError(subject, payload)
				
				data[subject][key] = payload
	
	with open(outf, 'w', newline='') as f:
		writer = csv.writer(f)
		
		row = ['Subject']
		row.extend(qs_init[k] for k in qs_init) # Not using .values for symmetry
		row.extend('H '+qs_final[k] for k in qs_final)
		row.extend('Z '+qs_final[k] for k in qs_final)
		writer.writerow(row)
		
		for subject, vals in data.items():
			row = [subject]
			row.extend(vals['I'][k] for k in qs_init)
			row.extend(vals['H'][k] for k in qs_final)
			row.extend(vals['Z'][k] for k in qs_final)
			writer.writerow(row)

if __name__ == '__main__':
	process_surveys('experiment.10.log', 'surveys.csv', {'PAE','PBE','PA1','PB1','PA2','PB2'})

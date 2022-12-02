import csv
from datetime import datetime
import json

from tqdm import tqdm

FORMAT = '%Y-%m-%d %H:%M:%S,%f'

def process(inf, outf, chosen=None):
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

if __name__ == '__main__':
	process('experiment.6.log', 'PA1.csv', {'PA1'})

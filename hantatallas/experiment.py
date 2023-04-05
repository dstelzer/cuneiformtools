import logging
from pathlib import Path
import time
import random
import json

import csv
import io

experimental_log = logging.getLogger('experiment') # Specifically deviating from recommended practice because this isn't meant to be module-specific, it's meant to be experiment-specific
exlog = experimental_log
experimental_log.setLevel(logging.INFO)
experimental_log.propagate = False

form = logging.Formatter('"{asctime}",{message}', style='{')
form.converter = time.gmtime

hand = logging.FileHandler(Path.cwd()/'experiment.log', encoding='utf8')
hand.setLevel(logging.INFO)

hand.setFormatter(form)
exlog.addHandler(hand)

def clean_data(subject, event, detail): # Use csv.writer to convert it to a valid row before writing to the log file
	# This ensures that we can interpret the experiment log as a CSV for processing
	# Columns: timestamp, subject, event, details
	data = io.StringIO()
	detail = json.dumps(detail) # Convert to JSON representation
	csv.writer(data).writerow((subject, event, detail))
	return data.getvalue()[:-1] # Remove trailing newline (logging handles it for us)

def record(subject, event, detail):
	exlog.info(clean_data(subject, event, detail))

filelists = {}
def image_from_which(which, lst):
	if lst not in filelists:
		parent = Path.cwd() / 'expimgs' / str(lst)
		filelists[lst] = sorted(parent.iterdir())
	return filelists[lst][which]

def get_sequence_length(lst):
	if lst not in filelists:
		image_from_which(0, lst) # The returned value doesn't matter, just need to make sure it's cached
	return len(filelists[lst])

permutations = {}
def choose_which(subject, index, lst, salt=''):
	if not subject.strip(): return index # for testing
	n_images = get_sequence_length(lst)
	if subject not in permutations or len(permutations[subject]) != n_images:
	#	random.seed(salt+subject)
		if n_images > 5:
			permutations[subject] = random.sample(range(n_images), k=n_images) # Random permutation of the numbers [0..n_images)
		else:
			permutations[subject] = list(range(n_images)) # For sample lists, don't bother shuffling, just go in lexicographic order (undamaged then damaged)
		record(subject, 'SHUFFLE', ' '.join(str(n) for n in permutations[subject]))
	if index < 0 or index > n_images: raise ValueError(index, n_images, subject, lst)
	return permutations[subject][index]

def choose_image(subject, index, lst):
	which = choose_which(subject, index, lst)
	img = image_from_which(which, lst)
	return img

def record_stimulus(subject, index, lst, system):
	which = choose_which(subject, index, lst)
	name = image_from_which(which, lst).stem
	record(subject, 'STIMULUS', {'list':lst, 'index':index, 'which':which, 'name':name, 'system':system})

def record_response(subject, index, lst, system, result):
	which = choose_which(subject, index, lst)
	name = image_from_which(which, lst).stem
	record(subject, 'RESPONSE', {'list':lst, 'index':index, 'which':which, 'name':name, 'system':system, 'result':result})

def record_survey(subject, result):
	record(subject, 'SURVEY', result)

def record_search(subject, code, regex, sort):
	record(subject, 'SEARCH', {'code':code, 'regex':regex, 'sort':sort})

def record_error(subject, type, details):
	record(subject, 'ERROR', {'type':type, 'details':details})

if __name__ == '__main__':
	from random import randint
	record_survey('TESTING', {'a':1,2:True,None:None,'r':randint(1,9)})
#	record('TESTING', f'{randint(1,9)},{randint(1,9)}', f'"{randint(1,9)}" \'{randint(1,9)}\'')

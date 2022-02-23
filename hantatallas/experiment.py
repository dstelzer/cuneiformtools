import logging
from pathlib import Path
import time

import csv
import io

experimental_log = logging.getLogger('experiment') # Specifically deviating from recommended practice because this isn't meant to be module-specific, it's meant to be experiment-specific
exlog = experimental_log
experimental_log.setLevel(logging.INFO)

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
	csv.writer(data).writerow((subject, event, detail))
	return data.getvalue()[:-1] # Remove trailing newline (logging handles it for us)

def record(subject, event, detail):
	exlog.info(clean_data(subject, event, detail))

if __name__ == '__main__':
	from random import randint
	record('TESTING', f'{randint(1,9)},{randint(1,9)}', f'"{randint(1,9)}" \'{randint(1,9)}\'')

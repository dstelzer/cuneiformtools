# Zarû = "winnow" in Akkadian (written MAR)
# It was the best I could think of following the theme of ettuttu

import pickle
from collections import Counter

class Tablet:
	def __init__(self, ident, glyphs=()):
		self.ident = ident
		self.glyphs = set(glyphs)

class Collection:
	def __init__(self, tablets=None):
		if tablets is None: tablets = dict()
		self.tablets = { ident: Tablet(ident, glyphs) for ident, glyphs in tablets.items() }
		
		self.glyphs = Counter()
		for ident, tab in self.tablets.items():
			self.glyphs.update(tab.glyphs) # Add them all to the counter
	
	@classmethod
	def from_file(cls, fn):
		with open(fn, 'rb') as f:
			tablets = pickle.load(f)
		return cls(tablets)
	
	def contribution(self, ident):
		tmp = self.glyphs.copy()
		tmp.subtract(self.tablets[ident].glyphs)
		tmp = +tmp # Remove zero counts
		return len(self.glyphs) - len(tmp)
	
	def discard(self, ident):
		self.glyphs.subtract(self.tablets[ident].glyphs)
		self.glyphs = +self.glyphs # Remove zeroes
		del self.tablets[ident]
	
	def autodiscard(self):
		worst = min(self.tablets.keys(), key=lambda i:self.contribution(i))
		cont = self.contribution(worst) # How much are we giving up here?
		self.discard(worst)
		return cont
	
	def count_tablets(self):
		return len(self.tablets)
	
	def count_glyphs(self):
		return len(self.glyphs)
	
	def optimize_tablets(self, maximum, verbose=True, stats=None):
		datapoints = Counter()
		if verbose: print(f'Optimizing to at most {maximum} tablets')
		if verbose: print(f'Starting with {self.count_glyphs()} distinct glyphs on {self.count_tablets()} tablets')
		zero_count = 0
		while True: # First, repeatedly discard as long as we're not truly removing anything
			val = self.autodiscard()
			if val > 0: break
			zero_count += 1
			datapoints[0] += 1
			if verbose: print('.', end='', flush=True)
		if verbose: print(f'Purged {zero_count} before first lost')
		if verbose: print(f'Current inventory: {self.count_glyphs()+val} distinct glyphs on {self.count_tablets()+1} tablets')
		if verbose: print(f'Lost {val} glyphs, down to {self.count_tablets()} tablets')
		datapoints[val] += 1
		while self.count_tablets() > maximum:
			loss = self.autodiscard()
			if verbose: print(f'Lost {loss} glyphs, down to {self.count_tablets()} tablets')
			datapoints[loss] += 1
		if verbose: print(f'Final result: {self.count_glyphs()} glyphs on {self.count_tablets()} tablets')
		if stats:
			with open(stats, 'a') as f:
				f.write('\n'.join(f'{a},{b}' for a,b in datapoints.items())+'\n')
	
	def save(self, fn):
		data = {ident:t.glyphs for ident,t in self.tablets.items()}
		with open(fn, 'wb') as f:
			pickle.dump(data, f)

if __name__ == '__main__':
	c = Collection.from_file('glyphs.pickle')
	c.optimize_tablets(20, stats='stats.csv')
	c.save('glyphs_20.pickle')
	c.optimize_tablets(10, stats='stats.csv')
	c.save('glyphs_10.pickle')
	c.optimize_tablets(1, stats='stats.csv')
	c.save('glyphs_1.pickle')

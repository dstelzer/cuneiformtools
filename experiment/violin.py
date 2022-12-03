import numpy as np
import scipy.stats as stat
import matplotlib.pyplot as plt

def violin(data, pos, color, width=1/3, fake=None, horizontal=False, linesonly=False, ax=None): # Manual version so we can fine-tune the behavior
	# Based on http://pyinsci.blogspot.com/2009/09/violin-plot-with-matplotlib.html
	if fake is None:
		k = stat.gaussian_kde(data)
		m = k.dataset.min()
		M = k.dataset.max()
		x = np.linspace(m, M, 100)
		y = k.evaluate(x)
		mu = np.mean(data)
		sigma = np.std(data)
		print(mu, sigma)
	else:
		mu, sigma = fake
		m = mu-2*sigma
		M = mu+2*sigma
		x = np.linspace(m, M, 100)
		y = stat.norm.pdf(x, mu, sigma)
	w1 = width
	w2 = width/2
	w3 = width/3
	y /= y.max(); y *= w1 # Scale to desired width
	if ax is None: ax = plt.gca()
	if horizontal:
		between = ax.fill_between
		lines = ax.vlines
	else:
		between = ax.fill_betweenx
		lines = ax.hlines
	if not linesonly:
		between(x, pos, pos+y, edgecolor=color, facecolor=color, alpha=0.5)
		between(x, pos, pos-y, edgecolor=color, facecolor=color, alpha=0.5)
	lines(mu, pos-w2, pos+w2, color=color)
	lines(mu+sigma, pos-w3, pos+w3, color=color)
	lines(mu-sigma, pos-w3, pos+w3, color=color)

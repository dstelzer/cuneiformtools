import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from violin import violin

def get_data(subjects):
	frames = [pd.read_csv(f'tagged/{s}.csv') for s in subjects]
	return pd.concat(frames)

def variation(data, seed=None): # Currently, uniform distribution between 0 and 1
	STRIP_SIZE = 0.5
	if seed is not None: np.random.seed(seed)
	return np.random.rand(len(data)) * STRIP_SIZE - STRIP_SIZE/2

def preprocess_data(data):
	return data[data['List'].str.startswith('P')] # Remove practice ones

def draw_mu_sigma(data, ax=None):
	if ax is None: ax = plt.gca()
	y, w1, w2 = 0, 1/3, 1/6
	color = 'blue'
	mu = np.mean(data)
	sigma = np.std(data)
	ax.vlines(mu, y-w1, y+w1, color=color, zorder=0)
	ax.vlines(mu+sigma, y-w2, y+w2, color=color, zorder=0)
	ax.vlines(mu-sigma, y-w2, y+w2, color=color, zorder=0)
#	ax.hlines(y, np.min(data), np.max(data), color=color, zorder=0)
	ax.hlines(y, mu-sigma, mu+sigma, color=color, zorder=0)

def plot_system_comparison():
	data = preprocess_data(get_data({'PA1', 'PB1'}))
	data_h = data[data['System']=='H']
	data_z = data[data['System']=='Z']
	xs_h_good = data_h[data_h['Accuracy']==1]['Duration']
	xs_z_good = data_z[data_z['Accuracy']==1]['Duration']
	xs_h_bad = data_h[data_h['Accuracy']==0]['Duration']
	xs_z_bad = data_z[data_z['Accuracy']==0]['Duration']
	
	fig, (ax1, ax2) = plt.subplots(2, sharex=True)
	ax1.scatter(x=xs_h_good, y=variation(xs_h_good, 21), c='cyan', edgecolors='black', label='Correct')
	ax1.scatter(x=xs_h_bad, y=variation(xs_h_bad, 2), c='red', edgecolors='black', label='Incorrect', marker='D')
	ax2.scatter(x=xs_z_good, y=variation(xs_z_good, 43), c='cyan', edgecolors='black')
	ax2.scatter(x=xs_z_bad, y=variation(xs_z_bad, 4), c='red', edgecolors='black', marker='D')
	draw_mu_sigma(xs_h_good, ax1)
	draw_mu_sigma(xs_z_good, ax2)
	
	plt.xlabel('Time taken (sec)')
	ax1.set_yticks(())
	ax2.set_yticks(())
	ax1.set_ylabel('Hantatallas')
	ax2.set_ylabel('Zeichenlexikon')
	ax1.legend()
	plt.xlim(left=0)
	plt.show()

def old():
	data = get_data({'PA1', 'PB1'})
	variation = np.random.rand(len(data))
	xs = data['Duration']
	ys = (data['System']=='H') + variation
	cs = data['Accuracy']
	data_h = data[data['System']=='H']
	data_z = data[data['System']=='Z']
	xs_h = data_h[data_h['Accuracy']==1]['Duration']
	xs_z = data_z[data_z['Accuracy']==1]['Duration']
	#fig, (ax1, ax2) = plt.subplots(2, sharex=True)
	violin(xs_h, 1, 'blue', horizontal=True, linesonly=True)
	violin(xs_z, 0, 'blue', horizontal=True, linesonly=True)
	plt.scatter(x=xs_h, y=ys, c=cs, edgecolors='black')
	plt.scatter(x=xs_h, y=ys, c=cs, edgecolors='black')
	plt.yticks([0, 1], ['Z', 'H'])
	plt.xlabel('Time taken (sec)')
	plt.ylabel('System')
	plt.show()

if __name__ == '__main__':
	plot_system_comparison()

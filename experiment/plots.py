import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stat

from tqdm import tqdm, trange

from violin import violin

def get_data(subjects):
	frames = [pd.read_csv(f'tagged/{s}.csv') for s in subjects]
	return pd.concat(frames)

def get_surveys(subjects):
	data = pd.read_csv('surveys.csv')
	return data[data['Subject'].isin(subjects)]

def variation(data, seed=None): # Currently, uniform distribution
	STRIP_SIZE = 0.5
	if seed is not None: np.random.seed(seed)
	return np.random.rand(len(data)) * STRIP_SIZE - STRIP_SIZE/2

def preprocess_data(data):
	return data[data['List'].str.startswith('P') & (data['Duration'] > 10) & (data['Duration']<600)] # Remove practice ones and extreme outliers

def add_t_statistic(data):
	mu, sigma = {}, {}
	subjects = data['Subject'].unique()
	for s in subjects:
		vals = data[(data['Subject']==s) & (data['Accuracy']==1)]['Duration']
		mu[s] = np.mean(vals)
		sigma[s] = np.std(vals)
	data['t-stat'] = data.apply((lambda row:
		(row['Duration'] - mu[row['Subject']]) / sigma[row['Subject']]
	), axis='columns') # Add new column
	return data

def draw_mu_sigma(data, ax=None, stderr=False):
	if ax is None: ax = plt.gca()
	y, w1, w2 = 0, 1/3, 1/6
	color = 'blue'
	mu = np.mean(data)
	sigma = np.std(data)
	if stderr: sigma /= np.sqrt(len(data))
	ax.vlines(mu, y-w1, y+w1, color=color, zorder=0)
	ax.vlines(mu+sigma, y-w2, y+w2, color=color, zorder=0)
	ax.vlines(mu-sigma, y-w2, y+w2, color=color, zorder=0)
#	ax.hlines(y, np.min(data), np.max(data), color=color, zorder=0)
	ax.hlines(y, mu-sigma, mu+sigma, color=color, zorder=0)

def plot_system_comparison():
	data = preprocess_data(get_data({'PA1', 'PB1', 'PAE', 'PB2'}))
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
	
#	plt.savefig('comparison.pdf')
	plt.show()

def plot_system_comparison_tstat():
	data = add_t_statistic(preprocess_data(get_data({'PA1', 'PB1', 'PAE', 'PB2'})))
	data_h = data[data['System']=='H']
	data_z = data[data['System']=='Z']
	xs_h_good = data_h[data_h['Accuracy']==1]['t-stat']
	xs_z_good = data_z[data_z['Accuracy']==1]['t-stat']
	xs_h_bad = data_h[data_h['Accuracy']==0]['t-stat']
	xs_z_bad = data_z[data_z['Accuracy']==0]['t-stat']
	
	fig, (ax1, ax2) = plt.subplots(2, sharex=True)
	ax1.scatter(x=xs_h_good, y=variation(xs_h_good, 21), c='cyan', edgecolors='black', label='Correct')
	ax1.scatter(x=xs_h_bad, y=variation(xs_h_bad, 2), c='red', edgecolors='black', label='Incorrect', marker='D')
	ax2.scatter(x=xs_z_good, y=variation(xs_z_good, 43), c='cyan', edgecolors='black')
	ax2.scatter(x=xs_z_bad, y=variation(xs_z_bad, 4), c='red', edgecolors='black', marker='D')
	draw_mu_sigma(xs_h_good, ax1, True)
	draw_mu_sigma(xs_z_good, ax2, True)
	
	plt.xlabel('Duration (t-statistic)')
	ax1.set_yticks(())
	ax2.set_yticks(())
	ax1.set_ylabel('Hantatallas')
	ax2.set_ylabel('Zeichenlexikon')
	ax1.legend()
#	plt.xlim(left=0)
	
	plt.savefig('comparison_tstat.pdf')
	plt.show()

def compare_difficulty():
	data = preprocess_data(get_data({'PA1', 'PB1', 'PAE', 'PB2'}))
	data = data[data['Accuracy']==1]
	data_h = data[data['System']=='H']
	data_z = data[data['System']=='Z']
	
	def get_by_diff(table, val):
		return table[table['Name'].str.startswith(str(val))]['Duration']
	
	def plot_difficulty(table, ax, tmp):
		xss = [get_by_diff(table, i) for i in range(5)]
		labels = ['Undamaged', 'Obscured', 'Lacking strokes', 'Lacking components', 'Obliterated']
		colors = ['cyan', 'green', 'yellow', 'orange', 'red']
		for i in range(5):
			ax.scatter(x=xss[i], y=variation(xss[i], 5*i+tmp), c=colors[i], edgecolors='black', label=labels[i])
	
	fig, (ax1, ax2) = plt.subplots(2, sharex=True)
	
	plot_difficulty(data_h, ax1, 1)
	plot_difficulty(data_z, ax2, 2)
	
	plt.xlabel('Time taken (sec)')
	ax1.set_yticks(())
	ax2.set_yticks(())
	ax1.set_ylabel('Hantatallas')
	ax2.set_ylabel('Zeichenlexikon')
	ax1.legend()
	plt.xlim(left=0)
	
	plt.savefig('difficulty.pdf')
	plt.show()

def compare_difficulty_tstat():
	data = add_t_statistic(preprocess_data(get_data({'PA1', 'PB1', 'PAE', 'PB2'})))
	data = data[data['Accuracy']==1]
	data_h = data[data['System']=='H']
	data_z = data[data['System']=='Z']
	
	def get_by_diff(table, val):
		return table[table['Name'].str.startswith(str(val))]['t-stat']
	
	def plot_difficulty(table, ax, tmp):
		xss = [get_by_diff(table, i) for i in range(5)]
		labels = ['Undamaged', 'Obscured', 'Lacking strokes', 'Lacking components', 'Obliterated']
		colors = ['cyan', 'green', 'yellow', 'orange', 'red']
		for i in range(5):
			ax.scatter(x=xss[i], y=variation(xss[i], 5*i+tmp), c=colors[i], edgecolors='black', label=labels[i])
	
	fig, (ax1, ax2) = plt.subplots(2, sharex=True)
	
	plot_difficulty(data_h, ax1, 1)
	plot_difficulty(data_z, ax2, 2)
	
	plt.xlabel('Time taken (t-statistic)')
	ax1.set_yticks(())
	ax2.set_yticks(())
	ax1.set_ylabel('Hantatallas')
	ax2.set_ylabel('Zeichenlexikon')
	ax1.legend()
#	plt.xlim(left=0)
	
	plt.savefig('difficulty_tstat.pdf')
	plt.show()

def compare_signs_tstat():
	data = add_t_statistic(preprocess_data(get_data({'PA1', 'PB1', 'PAE', 'PB2'})))
	data = data[data['Accuracy']==1]
	data_h = data[data['System']=='H']
	data_z = data[data['System']=='Z']
	
	def color(i): # Use the tab20 and tab20b colormaps
		if i < 20: return plt.cm.tab20(i)
		elif i < 40: return plt.cm.tab20b(i-20)
		else: raise ValueError(i)
	def shape(i):
		if i < 20: return 'o'
		elif i < 40: return 'D'
		else: raise ValueError(i)
	signs = list(data['Name'].unique())
	colormap = {s:color(i) for i,s in enumerate(signs)}
	shapemap = {s:shape(i) for i,s in enumerate(signs)}
	
	def plot_signs(table, ax, tmp):
		xs = table['t-stat']
		ys = variation(xs, tmp)
		cs = [colormap[s] for s in table['Name']]
		ss = [shapemap[s] for s in table['Name']] # want to use for `marker` but can't
		ax.scatter(x=xs, y=ys, c=cs, edgecolors='black')
	
	fig, (ax1, ax2) = plt.subplots(2, sharex=True)
	
	plot_signs(data_h, ax1, 1)
	plot_signs(data_z, ax2, 2)
	
	plt.xlabel('Time taken (t-statistic)')
	ax1.set_yticks(())
	ax2.set_yticks(())
	ax1.set_ylabel('Hantatallas')
	ax2.set_ylabel('Zeichenlexikon')
#	plt.xlim(left=0)
	
	plt.savefig('signs_tstat.pdf')
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

def check_distribution(which): # pass 'Z' or 'H'
	data = preprocess_data(get_data({'PA1', 'PB1', 'PAE', 'PBE', 'PA2'}))
	chosen = data[data['System']==which]
	durs = chosen['Duration']
	loc, scale = stat.expon.fit(durs)
	ex = stat.expon(loc=loc, scale=scale)
	print('Loc:', loc, 'Scale:', scale)
	xs = np.linspace(np.min(durs), np.max(durs), 1000)
	plt.hist(durs, density=True, bins=20, label='Data')
	plt.plot(xs, ex.pdf(xs), label='Exponential distribution')
	plt.xlabel('Time taken (sec)')
	plt.ylabel('Probability density')
	plt.yticks(())
	plt.title('Zeichenlexikon' if which=='Z' else 'Hantatallas')
	plt.legend()
	plt.show()

def both_distributions():
	data = preprocess_data(get_data({'PA1', 'PB1', 'PAE'}))
	data = data[data['Accuracy']==1] # Only hits
	low = np.min(data['Duration'])
	high = np.max(data['Duration'])
	
	def do(sigil, name, color):
		chosen = data[data['System']==sigil]
		durs = chosen['Duration']
		loc, scale = stat.expon.fit(durs)
		ex = stat.expon(loc=loc, scale=scale)
		print(name, 'Loc:', loc, 'Scale:', scale)
		xs = np.linspace(np.min(durs), np.max(durs), 1000)
		plt.hist(durs, density=True, bins=20, label=name, alpha=0.33, color=color, range=(low,high))
		plt.plot(xs, ex.pdf(xs), label=f'Exponential Dist', color=color)
	
	do('Z', 'Zeichenlexikon', 'r')
	do('H', 'Hantatallas', 'b')
	
	plt.xlabel('Time taken (sec)')
	plt.ylabel('Probability density')
	plt.yticks(())
	plt.legend()
	
	plt.savefig('distributions.pdf')
	plt.show()

def both_distributions_tstat():
	data = add_t_statistic(preprocess_data(get_data({'PA1', 'PB1', 'PAE', 'PB2'})))
	data = data[data['Accuracy']==1] # Only hits
	low = np.min(data['t-stat'])
	high = np.max(data['t-stat'])
	
	def do(sigil, name, color):
		chosen = data[data['System']==sigil]
		durs = chosen['t-stat']
		loc, scale = stat.expon.fit(durs)
		ex = stat.expon(loc=loc, scale=scale)
		print(name, 'Loc:', loc, 'Scale:', scale)
		xs = np.linspace(np.min(durs), np.max(durs), 1000)
		plt.hist(durs, density=True, bins=20, label=name, alpha=0.33, color=color, range=(low,high))
		plt.plot(xs, ex.pdf(xs), label=f'Exponential Dist', color=color)
	
	do('Z', 'Zeichenlexikon', 'r')
	do('H', 'Hantatallas', 'b')
	
	plt.xlabel('Time taken (t-score)')
	plt.ylabel('Probability density')
	plt.yticks(())
	plt.legend()
	
	plt.savefig('distributions_tstat.pdf')
	plt.show()

def both_distributions_separate():
	data = preprocess_data(get_data({'PA1', 'PB1', 'PAE'}))
	data = data[data['Accuracy']==1] # Only hits
	low = np.min(data['Duration'])
	high = np.max(data['Duration'])
	
	def do(sigil, name, color, axis):
		chosen = data[data['System']==sigil]
		durs = chosen['Duration']
		loc, scale = stat.expon.fit(durs)
		ex = stat.expon(loc=loc, scale=scale)
		print(name, 'Loc:', loc, 'Scale:', scale)
		xs = np.linspace(np.min(durs), np.max(durs), 1000)
		axis.hist(durs, density=True, bins=15, label=name, alpha=0.33, color=color, range=(low,high))
		axis.plot(xs, ex.pdf(xs), label=f'Exponential Dist', color=color)
		
		axis.set_ylabel('Probability density')
		axis.set_yticks(())
		axis.legend()
	
	fig, (ax1, ax2) = plt.subplots(2, sharex=True, sharey=True)
	
	do('Z', 'Zeichenlexikon', 'r', ax2)
	do('H', 'Hantatallas', 'b', ax1)
	ax2.set_xlabel('Time taken (sec)')
	
	plt.savefig('distrib_separate.pdf')
	plt.show()

def both_distributions_separate_tstat():
	data = add_t_statistic(preprocess_data(get_data({'PA1', 'PB1', 'PAE', 'PB2'})))
	data = data[data['Accuracy']==1] # Only hits
	low = np.min(data['t-stat'])
	high = np.max(data['t-stat'])
	
	def do(sigil, name, color, axis):
		chosen = data[data['System']==sigil]
		durs = chosen['t-stat']
		loc, scale = stat.expon.fit(durs)
		ex = stat.expon(loc=loc, scale=scale)
		print(name, 'Loc:', loc, 'Scale:', scale)
		xs = np.linspace(np.min(durs), np.max(durs), 1000)
		axis.hist(durs, density=True, bins=15, label=name, alpha=0.33, color=color, range=(low,high))
		axis.plot(xs, ex.pdf(xs), label=f'Exponential Dist', color=color)
		
		axis.set_ylabel('Probability density')
		axis.set_yticks(())
		axis.legend()
	
	fig, (ax1, ax2) = plt.subplots(2, sharex=True, sharey=True)
	
	do('Z', 'Zeichenlexikon', 'r', ax2)
	do('H', 'Hantatallas', 'b', ax1)
	ax2.set_xlabel('Time taken (t-statistic)')
	
	plt.savefig('distrib_separate_tstat.pdf')
	plt.show()

def pvalue():
	data = preprocess_data(get_data({'PA1', 'PB1', 'PAE', 'PB2'}))
	hdat = data[(data['System']=='H') & (data['Accuracy']==1)]['Duration']
	zdat = data[(data['System']=='Z') & (data['Accuracy']==1)]['Duration']
	print(stat.ks_2samp(hdat, zdat))

def pvalue_tstat():
	data = add_t_statistic(preprocess_data(get_data({'PA1', 'PB1', 'PAE', 'PB2'})))
	hdat = data[(data['System']=='H') & (data['Accuracy']==1)]['t-stat']
	zdat = data[(data['System']=='Z') & (data['Accuracy']==1)]['t-stat']
	print(stat.ks_2samp(hdat, zdat))

def ttest():
	data = add_t_statistic(preprocess_data(get_data({'PA1', 'PB1', 'PAE', 'PB2'})))
	hdat = data[(data['System']=='H') & (data['Accuracy']==1)]['t-stat']
	zdat = data[(data['System']=='Z') & (data['Accuracy']==1)]['t-stat']
	print(stat.ttest_ind(hdat, zdat, equal_var=False))

def bootstrap():
	data = preprocess_data(get_data({'PA1', 'PB1', 'PAE'}))
	hdat = data[(data['System']=='H') & (data['Accuracy']==1)]['Duration']
	zdat = data[(data['System']=='Z') & (data['Accuracy']==1)]['Duration']
	hmu = stat.bootstrap((hdat,), np.mean)
	zmu = stat.bootstrap((zdat,), np.mean)
	print(hmu)
	print(zmu)

def acc_time(which, system, tstat=False):
	stat = 't-stat' if tstat else 'Duration'
	data = add_t_statistic(preprocess_data(get_data(which)))
	data = data[data['System']==system]
	acc = np.mean(data['Accuracy'])
	mu = np.mean(data[data['Accuracy']==1][stat])
	sigma = np.std(data[data['Accuracy']==1][stat])
	return acc, mu, sigma

def acc_time_all(tstat=True):
	print('T-stat' if tstat else 'Duration')
	print(r'\textbf{Subject} & $a_H$ & $\mu_H$ & $\sigma_H$ & $a_Z$ & $\mu_Z$ & $\sigma_Z$ & $\mu_Z-\mu_H$ \\ \midrule')
	incl = {'PAE', 'PA1', 'PB1', 'PB2'}
	all = ('PAE', 'PBE', 'PA1', 'PB1', 'PA2', 'PB2')
	for which in all:
		h = acc_time({which}, 'H', tstat)
		z = acc_time({which}, 'Z', tstat)
		d = z[1] - h[1]
		t = r'\rmv' if which not in incl else ''
		print(f'{t} {which} & {t} {h[0]:.3f} & {t} {h[1]:.3f} & {t} {h[2]:.3f} & {t} {z[0]:.3f} & {t} {z[1]:.3f} & {t} {z[2]:.3f} & {t} {d:.3f} \\\\')
	h = acc_time(incl, 'H', tstat)
	z = acc_time(incl, 'Z', tstat)
	d = z[1] - h[1]
	print(f'Total & {h[0]:.3f} & {h[1]:.3f} & {h[2]:.3f} & {z[0]:.3f} & {z[1]:.3f} & {z[2]:.3f} & {d:.3f} \\\\')

def bootstrapping(data, key):
	column = data[key].unique()
	amount = len(column)
	chosen = np.random.choice(column, amount, replace=True)
	
#	new = pd.DataFrame().reindex_like(data) # Empty dataframe with same columns
	frames = [ data[data[key]==which] for which in chosen ]
	out = pd.concat(frames, ignore_index=True)
	return add_t_statistic(out)

def bootstrap(n, key, func):
	data = preprocess_data(get_data({'PAE','PA1','PB1','PB2'}))
	for _ in trange(n):
		replicate = bootstrapping(data, key)
		yield func(replicate)

def difference_in_means(data):
	tz = data[data['System']=='Z']['t-stat']
	th = data[data['System']=='H']['t-stat']
	return np.mean(tz) - np.mean(th)

def kolmogorov_smirnov(data):
	tz = data[data['System']=='Z']['t-stat']
	th = data[data['System']=='H']['t-stat']
	return stat.ks_2samp(tz,th).pvalue

def difference_in_locs(data):
	def loc(d): return stat.expon.fit(d)[0] # loc is 0, scale is 1
	tz = data[data['System']=='Z']['t-stat']
	th = data[data['System']=='H']['t-stat']
	return loc(tz) - loc(th)

def show_bootstrapping(n=1_000, func=difference_in_means, key='Name', fn=None, ax=None, title=None):
	if title is None: title = key
	res = list(bootstrap(n, 'Name', difference_in_means))
	p = sum(1 for d in res if d<=0) / len(res)
	print(title, 'p-value =', p)
	(plt if ax is None else ax).hist(res, bins=25)#, edgecolor='black')
	(plt.gca() if ax is None else ax).set_title(title)
	(plt.gca() if ax is None else ax).set_yticks(())
	if fn is not None: plt.savefig(fn)
	if ax is None: plt.show()

# 10_000, difference_in_means, 'Name', bootstrap_signs.pdf
# 10_000, difference_in_locs, 'Name', bootstrap_signs_loc.pdf
# 10_000, difference_in_means, 'Subject', bootstrap_subjects.pdf
# 10_000, difference_in_locs, 'Subject', bootstrap_subjects_loc.pdf

def bootstrap_all():
	input()
	fig, ((nw, ne), (sw, se)) = plt.subplots(2, 2, sharex=True, sharey=True)
	nw.tick_params('x', labelbottom=True)
	ne.tick_params('x', labelbottom=True)
	plt.subplots_adjust(hspace=0.3)
	n = 10_000
	show_bootstrapping(n=n, func=difference_in_means, key='Name', title='Signs (Means)', ax=nw)
	show_bootstrapping(n=n, func=difference_in_locs, key='Name', title='Signs (Distributions)', ax=ne)
	show_bootstrapping(n=n, func=difference_in_means, key='Subject', title='Subjects (Means)', ax=sw)
	show_bootstrapping(n=n, func=difference_in_locs, key='Subject', title='Subjects (Distributions)', ax=se)
	plt.savefig('bootstrap.pdf')
	plt.show()

def likert():
	data = get_surveys({'PAE','PA1','PB1','PB2'})
	columns = list(reversed(['H Difficult to use', 'Z Difficult to use', 'H Tiring to use', 'Z Tiring to use', 'H Certain of answers', 'Z Certain of answers']))
#	colors = ['red', 'orange', 'yellow', 'green', 'cyan']
	colors = [plt.cm.coolwarm(i) for i in (0.9, 0.8, 0.5, 0.2, 0.1)]
	colors[2] = '#aaaaaa'
	
	def howmany(col, val):
		return len(data[data[col]==val])
	
	left = np.zeros(len(columns))
	ys = list(range(len(columns), 0, -1)) # n..0
	ys = list(reversed(['Hantatallas\nDifficulty', 'Zeichenlexikon\nDifficulty', 'Hantatallas\nTiring', 'Zeichenlexikon\nTiring', 'Hantatallas\nCertainty', 'Zeichenlexikon\nCertainty']))
	for i in range(5):
		vals = [howmany(col, i+1) for col in columns]
		plt.barh(ys, width=vals, left=left, color=colors[i])
		left += vals
	
	plt.legend(['Not at all', 'A bit', 'Somewhat', 'Very', 'Extremely'], ncol=5, bbox_to_anchor=(1.015,1.1))
	plt.subplots_adjust(left=0.25, right=0.95)
	plt.xticks((0,1,2,3,4))
	plt.show()

if __name__ == '__main__':
	likert()
#	print(add_t_statistic(preprocess_data(get_data({'PBE','PA1','PA2','PB2'}))))

# Bootstrapping: we artificially choose to do the experiment differently
# Choose 16 glyphs from each list (randomly with replacement)
# Or, choose 2 participants from each group
# Or, choose 2 participants *for* each group, since list shows no effect
# Then, calculate difference of mean of t-scores
# Do this 10k times and plot distribution of means

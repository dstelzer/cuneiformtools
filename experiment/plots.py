import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from violin import violin

STRIP_SIZE = 0.25

def get_data(subjects):
	frames = [pd.read_csv(f'tagged/{s}.csv') for s in subjects]
	return pd.concat(frames)

data = get_data({'PA1', 'PB1'})
variation = np.random.rand(len(data)) * STRIP_SIZE - STRIP_SIZE/2
xs = data['Duration']
ys = (data['System']=='H') + variation
cs = data['Accuracy']
data_h = data[data['System']=='H']
data_z = data[data['System']=='Z']
xs_h = data_h[data_h['Accuracy']==1]['Duration']
xs_z = data_z[data_z['Accuracy']==1]['Duration']
violin(xs_h, 1, 'blue', horizontal=True, linesonly=True)
violin(xs_z, 0, 'blue', horizontal=True, linesonly=True)
plt.scatter(x=xs, y=ys, c=cs, edgecolors='black')
plt.yticks([0, 1], ['Z', 'H'])
plt.xlabel('Time taken (sec)')
plt.ylabel('System')
plt.show()

# Zoom into the 2.55-3.85 kHz band and median-whiten (per-row / per-column) to lift
# the drawn letters out of the harmonic noise.
import numpy as np
from scipy.io import wavfile
from scipy.signal import stft
from scipy.ndimage import median_filter
import matplotlib.pyplot as plt
sr,x=wavfile.read('2senses_puzzle.wav'); f,t,z=stft(x.astype(float)/32768,sr,nperseg=8192,noverlap=7680)
a=20*np.log10(np.abs(z)+1e-10)
sel=(f>=2550)&(f<=3850); a=a[sel]; f=f[sel]
for name,arr,lo,hi in [('focus_raw.png',a,-85,-20),('focus_whitened.png',a-median_filter(a,size=(19,1)),0,20),('focus_vertical.png',a-median_filter(a,size=(1,31)),0,20)]:
 fig,ax=plt.subplots(figsize=(26,7),dpi=120)
 ax.pcolormesh(t,f,arr,cmap='gray' if 'raw' in name else 'inferno',vmin=lo,vmax=hi,shading='auto')
 ax.set_xlim(1.8,15); ax.set_ylim(2550,3850); ax.set_xticks(np.arange(2,15,.5)); ax.grid(axis='x',alpha=.25)
 fig.tight_layout(); fig.savefig(name); plt.close(fig)

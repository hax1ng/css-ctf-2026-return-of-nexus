# Render STFT spectrograms of 2senses_puzzle.wav across three bands to find the
# hand-drawn lettering hidden in the 2.3-4.3 kHz region.
import numpy as np
from scipy.io import wavfile
from scipy.signal import stft
import matplotlib.pyplot as plt
sr,x=wavfile.read('2senses_puzzle.wav')
f,t,z=stft(x.astype(float)/32768,sr,nperseg=4096,noverlap=3584)
a=20*np.log10(np.abs(z)+1e-9)
for lo,hi,name,vr in [(2300,4300,'spectrogram_letters.png',(-100,-25)),(0,5000,'spectrogram_low.png',(-100,-25)),(4500,17500,'spectrogram_high.png',(-100,-25))]:
 fig,ax=plt.subplots(figsize=(24,6),dpi=140)
 idx=(f>=lo)&(f<=hi)
 ax.pcolormesh(t,f[idx],a[idx],cmap='inferno',vmin=vr[0],vmax=vr[1],shading='auto')
 ax.set_xlim(0,17); ax.set_ylim(lo,hi); ax.set_xticks(np.arange(0,17.1,0.5)); ax.grid(axis='x',alpha=0.3)
 fig.tight_layout(); fig.savefig(name); plt.close(fig)
 print(name)

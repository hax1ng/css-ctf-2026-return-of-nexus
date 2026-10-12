# Log-frequency spectrogram, to double-check the drawn word reads title-case "Chinaski".
import numpy as np
from scipy.io import wavfile
from scipy.signal import stft
import matplotlib.pyplot as plt
sr,x=wavfile.read('2senses_puzzle.wav'); f,t,z=stft(x.astype(float)/32768,sr,nperseg=4096,noverlap=3584)
a=20*np.log10(np.abs(z)+1e-10)
for name,lo,hi,vr in [('logspec.png',100,18000,(-90,-25)),('logspec_bright.png',100,18000,(-75,-35))]:
 fig,ax=plt.subplots(figsize=(24,11),dpi=130); idx=(f>=lo)&(f<=hi)
 ax.pcolormesh(t,f[idx],a[idx],cmap='inferno',vmin=vr[0],vmax=vr[1],shading='auto')
 ax.set_yscale('log'); ax.set_ylim(lo,hi); ax.set_xlim(0,17); ax.set_xticks(np.arange(0,17.1,.5)); ax.grid(axis='x',alpha=.1)
 fig.tight_layout(); fig.savefig(name); plt.close(fig)

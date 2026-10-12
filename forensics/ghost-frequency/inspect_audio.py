# Spectrogram both channels of KBR17_blackbox.wav (22 MiB, omitted here for size).
import wave,numpy as np,matplotlib.pyplot as plt
from scipy.signal import stft
with wave.open('KBR17_blackbox.wav') as f: a=np.frombuffer(f.readframes(f.getnframes()),np.int16).reshape(-1,2)
fs=48000
fig,ax=plt.subplots(2,1,figsize=(16,9),constrained_layout=True)
for c in (0,1):
 x=a[:10*fs:4,c]; freq,t,s=stft(x,fs/4,nperseg=256,noverlap=200)
 mask=(freq<3500)&(freq>500)
 ax[c].pcolormesh(t,freq[mask],20*np.log10(np.abs(s[mask])+1),cmap='magma',vmin=0,vmax=85,shading='auto');ax[c].set_title(f'Channel {c}, first 10s'); ax[c].set_ylabel('Hz')
plt.savefig('initial_spectrogram.png',dpi=120)

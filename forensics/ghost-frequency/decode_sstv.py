# Decode the left-channel Martin M1 SSTV frame from KBR17_blackbox.wav
# (22 MiB, omitted here for size) into decoded_martin_m1.png.
import wave,numpy as np
from scipy.signal import hilbert
from PIL import Image
with wave.open('KBR17_blackbox.wav') as w:
 a=np.frombuffer(w.readframes(w.getnframes()),np.int16).reshape(-1,2)[::4,0].astype(np.float64)
fs=12000
phase=np.unwrap(np.angle(hilbert(a)))
frequency=np.diff(phase)*fs/(2*np.pi)
# VIS code 44: Martin M1, 320x256, 446.446 ms/line.
t0=.91
line=.446446
sync=.004862
porch=.000572
scan=.146432
sep=.000572
image=np.empty((256,320,3),dtype=np.uint8)
for row in range(256):
 base=t0+row*line+sync+porch
 for j,channel in enumerate([1,2,0]): # Martin sends G, B, R
  center=base+j*(scan+sep)+(np.arange(320)+.5)*scan/320
  idx=np.round(center*fs).astype(int)
  val=np.array([np.median(frequency[k-2:k+3]) for k in idx])
  image[row,:,channel]=np.clip(np.rint((val-1500)*255/800),0,255).astype(np.uint8)
Image.fromarray(image).save('decoded_martin_m1.png')

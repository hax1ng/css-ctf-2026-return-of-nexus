#!/usr/bin/env python3
"""Reconstruct, re-encrypt, and decode the unique recovered preimages."""
import json
import numpy as np
from source import encrypt_vector, decode_frame

d=json.load(open('prepared.json'))
archive=json.load(open('out.txt'))
p=17
sols=[
    ([4,16,6,11],[7,14,8,16,9,9,5,16,12,11,2,1]),
    ([4,14,12,0],[10,0,4,14,2,7,14,10,15,12,10,9]),
    ([16,7,1,3],[15,3,14,13,7,6,0,0,5,6,5,4]),
]
B=np.array(d['B'],dtype=np.int64)
E=np.array(d['E'],dtype=np.int64)
Din=np.array(d['Dinv'],dtype=np.int64)
O=np.array(d['oil'],dtype=np.int64)
V=np.array(d['vinegar'],dtype=np.int64)
WC=np.array(d['Wcoeff'],dtype=np.int64)
WM=d['Wmon']

def eval_w(x):
    val=np.zeros(16,dtype=np.int64)
    for j,mon in enumerate(WM):
        term=1
        for k in mon: term=term*int(x[k])%p
        val=(val+WC[:,j]*term)%p
    return val

digits=[]
for k,(vinegar,oil) in enumerate(sols):
    y=(V@np.array(vinegar)+O@np.array(oil))%p
    base=E@y%p
    delta=(np.array(d['target_w'][k])-eval_w(base))%p
    x=(base+B@(Din@delta%p))%p
    ct=encrypt_vector(archive['public_key'],x.tolist())
    assert ct==archive['ciphertext']['blocks'][k]
    print('block',k,'verified x =',x.tolist())
    digits.extend(x.tolist())

plaintext=decode_frame(digits,p,32)
print('plaintext:',repr(plaintext))
print('UTF-8:',plaintext.decode('utf-8'))

#!/usr/bin/env python3
"""Convert prepared.json into a simple integer stream for the C++ solver."""
import json

d=json.load(open('prepared.json'))
with open('numeric.txt','w') as f:
    def put(v):
        if isinstance(v,list):
            for x in v: put(x)
        else:
            f.write(str(v)+' ')
    put(d['Hvv']); put(d['Hvo'])
    for block in d['blocks']:
        for key in ('const','lv','lo','target'): put(block[key])

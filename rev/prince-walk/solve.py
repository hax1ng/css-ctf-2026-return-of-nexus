#!/usr/bin/env python3
"""Locally emulate prince_walk's coordinate-keyed response VM."""
import struct
from pathlib import Path

MASK = 0xffffffff
X = Y = 999999
DATA = Path(__file__).with_name('prince_walk').read_bytes()
TABLE = [struct.unpack_from('<II', DATA, 0x4a80 + i * 8) for i in range(0x2080)]


def rol(x, n):
    n &= 31
    x &= MASK
    return ((x << n) | (x >> ((32 - n) & 31))) & MASK


def mix(x):
    x &= MASK
    x = ((x >> 16) ^ x) * 0x7feb352d & MASK
    x = ((x >> 15) ^ x) * 0x846ca68b & MASK
    return ((x >> 16) ^ x) & MASK


regs = [mix(((i+1)*0x9e3779b9) ^ X ^ rol(Y, i+1)) for i in range(16)]
state = mix((rol(Y, 0x13) + X) ^ 0xa4093822)
output = bytearray(128)
seen = set()
for i in range(0x2080):
    j = (i * 0xd9 + 0xcd6) % 0x2080
    enc_word, enc_imm = TABLE[j]
    word = mix((i*0x9e3779b9) ^ state) ^ enc_word
    imm = mix(i + state + 0x6a09e667) ^ enc_imm
    op = word & 0xff
    dst = (word >> 8) & 15
    src1 = (word >> 12) & 15
    src2 = (word >> 16) & 15
    rotation = (word >> 20) & 31
    a, b = regs[src1], regs[src2]
    if op == 0xff:
        value = rol(a ^ imm, (b ^ rotation) & 31)
    elif op == 0xb3:
        value = (a & imm) | ((~imm) & b)
    elif op == 0x8b:
        value = a + rol(b, rotation) + imm
    elif op == 0x83:
        pos = imm >> 25
        if pos >= 128 or pos in seen:
            raise ValueError(f'bad store at {i}: {pos}')
        char = (imm ^ a ^ rol(b, rotation)) & 255
        output[pos] = char
        seen.add(pos)
        value = regs[dst] ^ ((pos + char) * 0x45d9f3b)
    elif op == 0x71:
        value = a - rol(b ^ imm, rotation)
    elif op == 0x48:
        value = rol(b + imm, rotation) ^ a
    elif op == 0x12:
        value = mix(imm + a + b)
    elif op == 0x31:
        value = (imm | 1) * ((imm + b) ^ a)
    else:
        raise ValueError(f'bad opcode {op:#x} at {i}')
    regs[dst] = value & MASK
    state = ((i * 0x3c6ef372) + imm + rol(regs[dst] ^ regs[src1] ^ state ^ word, 9)) & MASK

if len(seen) != 128:
    raise ValueError(f'only {len(seen)} stores')
length = output[0]
body = output[1:1+length]
fnv = 0x811c9dc5
for ch in body:
    fnv = ((fnv ^ ch) * 0x1000193) & MASK
stored = struct.unpack_from('<I', output, 1+length)[0]
print('length', length, 'fnv', hex(fnv), 'stored', hex(stored))
print(body.decode())

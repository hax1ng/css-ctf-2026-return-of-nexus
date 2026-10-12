#!/usr/bin/env python3
"""Recover Chrono II plaintext from timestamped ciphertext captures.

A 77-tick additive wheel advances 43 slots per alphanumeric position.
The known event flag prefix identifies every wheel slot; digits use that
same slot's shift modulo 10.
"""
import datetime as dt
import json
from pathlib import Path

PERIOD = 77
STEP = 43
KNOWN_PREFIX = 'CSSCTF'

def load(path):
    return json.loads(Path(path).read_text())

def epoch(value):
    return int(dt.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp())

def main():
    train = load('capture.json')
    check = load('capture_validation.json')
    base = epoch(train[0]['timestamp'])
    wheel = {}
    for row in train:
        tick = epoch(row['timestamp']) - base
        for index, plain in enumerate(KNOWN_PREFIX):
            slot = (tick + STEP * index) % PERIOD
            shift = (ord(row['ciphertext'][index]) - ord(plain)) % 26
            assert slot not in wheel or wheel[slot] == shift
            wheel[slot] = shift
    assert len(wheel) == PERIOD

    def decrypt(row):
        tick = epoch(row['timestamp']) - base
        index = 0
        result = []
        for cipher in row['ciphertext']:
            if cipher.isupper():
                result.append(chr((ord(cipher) - 65 - wheel[(tick + STEP * index) % PERIOD]) % 26 + 65))
            elif cipher.islower():
                result.append(chr((ord(cipher) - 97 - wheel[(tick + STEP * index) % PERIOD]) % 26 + 97))
            elif cipher.isdigit():
                result.append(str((int(cipher) - wheel[(tick + STEP * index) % PERIOD]) % 10))
            else:
                result.append(cipher)
                continue
            index += 1
        return ''.join(result)

    results = {decrypt(row) for row in train + check}
    assert len(results) == 1, results
    print(f'Recovered {len(wheel)} wheel slots; {len(train)} training and {len(check)} validation records agree.')
    print(next(iter(results)))

if __name__ == '__main__':
    main()

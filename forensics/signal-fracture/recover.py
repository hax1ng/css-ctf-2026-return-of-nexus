#!/usr/bin/env python3
"""Recover the Nexus object from catalog-verified NXFR records.

Requires KBR17_relay.img (64 MiB MBR disk image, omitted from this repo for
size) beside this script; the ext4 cache blobs, scheduler catalog (relay.db)
and the uplink PCAP are committed under recovered/ and alongside.
"""
import hashlib
import sqlite3
import struct
import subprocess
import zlib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SESSION = '6E2C17A9'
catalog = dict(sqlite3.connect(ROOT / 'recovered/relay.db').execute(
    'SELECT seq, expected_sha256 FROM fragments WHERE session=?', (SESSION,)))
records = defaultdict(list)


def check(data, source, offset=0):
    if len(data) < 20 or data[:4] != b'NXFR':
        return
    session, seq, total, length, crc = struct.unpack('>IHHII', data[4:20])
    if length > len(data) - 20 or total == 0 or seq >= total:
        return
    payload = data[20:20+length]
    digest = hashlib.sha256(payload).hexdigest()
    crc_ok = zlib.crc32(payload) == crc
    match = f'{session:08X}' == SESSION and catalog.get(seq) == digest
    print(f'{source} @0x{offset:x}: session={session:08X} seq={seq}/{total} len={length} crc={crc_ok} catalog={match} hash={digest}')
    if match and crc_ok:
        records[seq].append((source, payload))


image = (ROOT / 'KBR17_relay.img').read_bytes()
at = 0
while (at := image.find(b'NXFR', at)) != -1:
    check(image[at:], 'image', at)
    at += 4
for blob in (ROOT / 'recovered').glob('*.blob'):
    check(blob.read_bytes(), blob.name)

output = subprocess.check_output(['tshark', '-r', str(ROOT / 'KBR17_uplink.pcap'),
                                  '-Y', 'udp.port == 4711', '-T', 'fields', '-e', 'data.data'], text=True)
for num, line in enumerate(output.splitlines(), 1):
    check(bytes.fromhex(line), f'pcap record {num}')

missing = sorted(set(catalog) - set(records))
print('catalog fragment count:', len(catalog), 'found:', sorted(records), 'missing:', missing)
if not missing:
    payload = b''.join(records[i][0][1] for i in sorted(catalog))
    out = ROOT / 'recovered/emergency_burst_17.bin'
    out.write_bytes(payload)
    print('reassembled:', out, 'size:', len(payload), 'sha256:', hashlib.sha256(payload).hexdigest())

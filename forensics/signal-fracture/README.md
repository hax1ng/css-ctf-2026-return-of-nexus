# Signal Fracture

**Category:** Forensics · **Points:** 100 · **Solves:** 401 · **Challenge ID:** 19

> The scheduler catalog was intact even though the spool index had been purged, and uplink retries may have produced more than one copy of the same fragment.

## Challenge

KBR-17 came back online for only fourteen seconds before the Nexus fabric collapsed. A
passive tap captured the relay's final uplink, and technicians imaged the relay drive
exactly as it was after emergency shutdown. The object we want (`emergency_burst_17`) was
split into eight ordered fragments and scattered across three locations — some of them in
duplicate, with a stale copy mixed in among the good ones.

**Attachment:** `Signal_Fracture.zip` → a 64 MiB MBR disk image + a PCAP (see [Files](#files)).

## Initial analysis

The archive contains `KBR17_relay.img` (64 MiB, MBR) and `KBR17_uplink.pcap`.

```console
$ mmls KBR17_relay.img         # p1 = ext4 @ sector 2048, p2 = raw spool ring
```

Partition 1 is ext4; `icat` pulls out the maintenance note, a transfer log, the fragment
format spec, the SQLite scheduler catalog, and three cache blobs — all committed under
[`recovered/`](recovered/). The maintenance note sets the rules:

> The transfer manager keeps authoritative ordering and hashes in the scheduler catalog.
> The raw spool is a ring buffer: purging removes its index but does not zero old records.
> Passive uplink taps may contain multiple copies of a retried fragment.

The fragment wire format (`recovered/fragment-format.txt`) — big-endian **NXFR** records:

```
0x00  magic = "NXFR"       0x0C  payload_length (u32)
0x04  session_id (u32)     0x10  payload_crc32  (u32)
0x08  sequence (u16)       0x14  payload bytes ...
0x0A  total_fragments (u16)
```

Crucially: *the scheduler catalog stores SHA-256 over the PAYLOAD BYTES ONLY, and a repeated
record is authoritative only if its payload hash matches the catalog.* So CRC32 alone is not
enough — a stale retry can still carry a valid CRC.

## Vulnerability / core concept

**Carving duplicate fragments and disambiguating by an authoritative hash.** The eight
fragments of session `6E2C17A9` live in three places:

- **ext4 cache blobs** (`recovered/inode_3{0,1,2}.blob`) → sequences 1 and 4
- **raw spool ring** in partition 2 of the image (index purged but records not zeroed) →
  sequences 0, 2, 5
- **PCAP** (passive uplink tap, UDP port 4711) → sequences 3, 6, 7

The traps:

- The spool ring holds a **second CRC-valid copy of sequence 2** whose payload hash does
  **not** match the catalog — a leftover ring record.
- The PCAP holds the **first CRC-valid uplink copy of sequence 6** that is **stale** (a
  retry), again CRC-OK but catalog-mismatched.

Trusting CRC or "first copy wins" reassembles a corrupt object. The scheduler catalog's
per-fragment SHA-256 is the only authority.

## Exploitation

[`recover.py`](recover.py) loads the catalog from `relay.db`, then scans every candidate
source for `NXFR` records, parses the header, and accepts a fragment **only** when both the
CRC32 checks out *and* the payload SHA-256 equals the catalog entry for that sequence:

```python
session, seq, total, length, crc = struct.unpack('>IHHII', data[4:20])
payload = data[20:20+length]
crc_ok  = zlib.crc32(payload) == crc
match   = f'{session:08X}' == SESSION and catalog.get(seq) == sha256(payload).hexdigest()
if match and crc_ok:
    records[seq].append((source, payload))
```

It sweeps the raw image for `NXFR` magic, reads the ext4 cache `*.blob` files, and pulls the
uplink payloads out of the PCAP with tshark:

```console
$ tshark -r KBR17_uplink.pcap -Y 'udp.port == 4711' -T fields -e data.data
```

With all eight catalog-verified payloads in hand, it joins sequences 0..7 in order:

```console
$ python3 recover.py
image @0x...: seq=2/8 crc=True  catalog=False   <-- stale ring copy, rejected
pcap record 5: seq=6/8 crc=True catalog=False   <-- stale retry, rejected
...
reassembled: recovered/emergency_burst_17.bin size: 6725 sha256: 36d5a38f...2cb8
```

The 6,725-byte object passes `gzip -t` and extracts to a TAR containing
`final_message.txt`, `burst_metadata.json`, and `telemetry.bin`. The authorization token is
in the message (committed at `recovered/burst/final_message.txt`):

```
KBR-17 EMERGENCY BURST // FINAL RECOVERY
Authorization token: CSSCTF{fragment_t3ll_th3_st0ry}
```

## Flag

```
CSSCTF{fragment_t3ll_th3_st0ry}
```

## Files

- `KBR17_relay.img` — 64 MiB MBR disk image, **omitted** (reproducible challenge input).
  Needed to re-run the spool-ring carving for sequences 0/2/5.
- `Signal_Fracture.zip` — 81 KiB archive that unpacks to the 64 MiB image + PCAP, **omitted**
  (it *is* the disk image). SHA-256 `ec060ca8cf0cebec1c6f88b8fd8e3f54789121ca2019765dd292d50ee5d11ead`.
- `KBR17_uplink.pcap` — 5.2 KiB passive-tap capture, committed (sequences 3/6/7).
- `recovered/` — scheduler catalog (`relay.db`), ext4 cache blobs, maintenance note,
  transfer log, fragment-format spec, and the extracted burst (`burst/final_message.txt`,
  `burst/burst_metadata.json`).

## Key takeaways

- CRC32 proves integrity *of a copy*, not that the copy is the right one — a stale retry is
  internally consistent. Use the authoritative hash list when one exists.
- Purging a ring-buffer index does not zero its records; raw-partition carving still yields
  old payloads.
- When fragments come from multiple channels (disk, raw spool, network), key every candidate
  by `(session, sequence)` and let the catalog pick the winner rather than "first seen".

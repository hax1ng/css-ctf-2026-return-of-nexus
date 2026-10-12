# Ghost Frequency

**Category:** Forensics · **Points:** 115 · **Solves:** 364 · **Challenge ID:** 18

> The recorder captured two maintenance channels: one for visual diagnostics, one for low-rate packet telemetry — and the damaged uplink may have retried stale data in its final minutes.

## Challenge

KBR-17's maintenance black box survived The Severance, but its final transmission never
reached the Nexus archive. Relay documentation says the recorder captured **two channels
simultaneously**: one carried visual diagnostics, the other low-rate packet telemetry.
Reconstruct the final transmission from both — beware of stale retried data.

**Attachment:** `KBR17_blackbox.wav` (stereo 48 kHz/16-bit, 115.2 s — 22 MiB, omitted here,
see [Files](#files)).

## Initial analysis

The WAV is stereo; the two channels carry two different modulations. A quick spectrogram of
each channel (see [`inspect_audio.py`](inspect_audio.py)) shows the left channel sweeping like
an image transmission and the right channel as narrow-band FSK tones.

- **Left channel — SSTV.** The leader/VIS header decodes to **VIS code 44 = Martin M1**
  (320×256, 446.446 ms/line, G-B-R scan order).
- **Right channel — Bell 202 AFSK**, 1200 baud, 8N1 packet telemetry.

## Vulnerability / core concept

**Two-channel demodulation + parity recovery + stale-retry rejection.** The transmission is a
GZIP archive split into eight 1024-byte DATA blocks `D0..D7`, sent over the FSK channel, with
redundancy so it can be rebuilt even though two blocks are missing and one block arrives as a
stale duplicate:

- The **SSTV image is the control sheet**: it prints the session (`NX-771`), the FSK
  parameters, the block layout, the two XOR parity groups, and — critically — the
  **authoritative CRC32 of every block**.
- The FSK channel carries the actual data packets (plus a decoy session `NX-770`).
- Two parity blocks let you reconstruct the two missing data blocks; the per-block CRC list
  from the image tells you which of the duplicate/retried packets to trust.

Parity groups (from the decoded image):

```
PARITY_A = D0 ^ D1 ^ D2 ^ D3     ->  recovers missing D2
PARITY_B = D4 ^ D5 ^ D6 ^ D7     ->  recovers missing D5
```

## Exploitation

**1. Decode the SSTV control sheet.** [`decode_sstv.py`](decode_sstv.py) FM-demodulates the
left channel (Hilbert transform → instantaneous frequency), samples Martin M1 timing, and
renders the frame. It yields: session `NX-771`; Bell 202 / 1200 / 8N1; DATA = base64,
1024-byte blocks; 5757-byte GZIP archive; parity groups A/B; and the authoritative CRC32 for
`D0..D7`.

**2. Demodulate the telemetry channel losslessly:**

```console
$ minimodem --rx -f channel1.wav -q 1200 > telemetry_raw.txt
```

This gives ten `NXPKT|...` lines (committed as [`telemetry_raw.txt`](telemetry_raw.txt)). Each
packet base64-decodes to its advertised `LEN` and passes its own `WIRECRC`.

**3. Reassemble with CRC arbitration + parity.** [`reassemble.py`](reassemble.py) keeps only
`NX-771` packets whose payload CRC matches the **authoritative SSTV CRC** (dropping the
`NX-770` decoy), XOR-recovers the two missing blocks, then restores the archive:

```python
expected = {0:0xA66FEFC8, 1:0x7C3DCD2A, 2:0x1812F5CD, 3:0xBB1810C0,
            4:0xD6CCE79E, 5:0x6B9F6550, 6:0x2A18C562, 7:0x3D924BBF}
# D6 retry 1 (C04CF7F5) passes WIRECRC but is STALE -> rejected
# D6 retry 2 (2A18C562) matches the SSTV CRC -> used
recovered = bytes(a^b^c^d for a,b,c,d in zip(parity['A'], D0, D1, D3))  # -> D2
```

The subtle trap: **D6 retry 1 has a valid wire CRC but the wrong payload** — using it would
corrupt parity group B and the recovered D5. Only D6 retry 2 matches the authoritative CRC.

**4. Fix the archive and extract.** Concatenating `D0..D7` and trimming to 5757 bytes gives a
GZIP whose first two magic bytes were zeroed. Restoring `1F 8B` (documented on the SSTV sheet)
makes GZIP decompression succeed with its internal CRC/size checks, yielding a 10,240-byte
POSIX TAR:

```console
$ python3 reassemble.py
recovered 2 0X1812F5CD expected 0X1812F5CD
recovered 5 0X6B9F6550 expected 0X6B9F6550
original magic: 00000800000000000203
content bytes 10240 prefix b'NX-771/final_message.txt...'
```

The TAR's `NX-771/final_message.txt` (committed under [`recovered/`](recovered/NX-771/)) holds
the flag:

```
NEXUS EMERGENCY TRANSMISSION  KBR-17 // SESSION NX-771
CSSCTF{th3_gh0st_fr3qu3ncy_w4s_n3v3r_s1l3nt}
```

## Flag

```
CSSCTF{th3_gh0st_fr3qu3ncy_w4s_n3v3r_s1l3nt}
```

## Files

- `KBR17_blackbox.wav` — 22 MiB stereo capture, **omitted** (reproducible challenge input).
  SHA-256 `64de518e4fec44e8127078fcb93a2acdf610ca5b8af9608187bfdd2970321cae`.
- `channel1.wav` — 11 MiB right-channel extract fed to `minimodem`, **omitted** (solver
  intermediate, regenerable from the stereo WAV).
- Decoded SSTV / spectrogram PNGs — **omitted** (solver-generated renders).
- `inspect_audio.py`, `decode_sstv.py` — need the WAV above (omitted).
- `reassemble.py` + `telemetry_raw.txt` — committed and self-contained: re-running
  `reassemble.py` reproduces the archive and the flag from the committed telemetry.
- `recovered/NX-771/final_message.txt` — the extracted final message.

## Key takeaways

- A multi-channel recording can hide an out-of-band "control sheet" — here the SSTV image
  carries the parameters and the authoritative CRCs that make the noisy FSK channel decodable.
- Per-packet wire CRCs only prove a packet arrived intact, not that it is the *current* data;
  a stale retry with a valid CRC still corrupts XOR parity. Arbitrate with an independent
  authoritative hash.
- XOR parity (`P = D_a ^ D_b ^ D_c ^ D_d`) recovers exactly one missing member per group — pair
  it with a correct-block set and you can rebuild a transmission with holes.

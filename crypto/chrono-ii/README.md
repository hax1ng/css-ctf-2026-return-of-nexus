# Chrono II

**Category:** Cryptography · **Points:** 100 · **Solves:** 385 · **Challenge ID:** 21

> We have again intercepted their talk and the cipher text, but this time it seems like its always changing. Help us!

## Challenge

The sequel to [Chrono I](../chrono-i/). This time there is no static ciphertext — only a live service that keeps re-encrypting the flag:

```
"The Time is ticking, it will never stop, no one will ever decrypt it"

Flag Format: CSSCTF{...}

Connection Information
- http://REMOTE_HOST:8001
```

The web UI streams a feed and exposes `/capture.json`, which returns a rolling log of **60 UTC-timestamped ciphertexts** (one per second), each a 40-character string of the same shape as the flag, e.g.:

```json
[
  {"timestamp":"2026-09-30T16:27:24Z","ciphertext":"GYVSCK{bn6_ca7fn_a3p9vl3za_4gqyb_b3k8yi}"},
  {"timestamp":"2026-09-30T16:27:25Z","ciphertext":"OVBJDK{xu8_sp9fm_z1z0wg2wz_4ajze_a1p2pk}"},
  {"timestamp":"2026-09-30T16:27:26Z","ciphertext":"CHZFWO{dk9_lv0ks_s4y0pk3za_4afvl_x4o7ve}"},
  ...
]
```

The same flag is encrypted differently every second — the cipher is keyed by time.

## Initial analysis

Two captures were taken from the authorized team endpoint a few minutes apart and saved as [`capture.json`](capture.json) (training) and [`capture_validation.json`](capture_validation.json) (validation). The simple capture utility is included as [`capture_timed.py`](capture_timed.py) / [`capture_bursts.py`](capture_bursts.py).

Observations across the rows:

- Every ciphertext has an identical 40-character layout: a six-letter uppercase prefix, braces, and underscore-separated lowercase/digit groups. The plaintext never changes; only the encryption does.
- The prefix is always a known plaintext — it decrypts to `CSSCTF`.
- Looking at how a single character position changes from one second (tick) to the next, the per-tick differences in one position reappear in another position once you apply a fixed offset. That is the signature of a **rotating shift wheel**: the same sequence of additive shifts, read from a different starting slot each second and each character.

## Vulnerability / core concept

The service uses a **time-seeded rotating Vigenère wheel** with these parameters:

- The wheel has **`PERIOD = 77`** additive shift slots.
- For a message at UTC tick `t` (seconds since a reference), the shift applied to character index `i` is read from slot `(t + STEP·i) mod 77`, where **`STEP = 43`**.
- The wheel only advances on **alphanumeric** characters — braces and underscores are passed through and do not consume a slot (same trick as Chrono I, generalised).
- Letters are shifted mod 26 (case-preserved); digits are shifted mod 10, using the *same* slot value.

Because the plaintext (the flag) is constant and its six-character prefix `CSSCTF` is known, every capture row leaks the shift values of several wheel slots. The prefix letters at consecutive ticks sweep across all 77 slots, so **a single 60-row capture recovers the entire wheel**. Once all 77 slots are known, every character of every row decrypts — the wheel is the key, and time only tells you where to start reading it.

## Exploitation

The recovery is in [`solve.py`](solve.py), which derives the wheel from the captures rather than hard-coding the flag.

**Step 1 — recover the wheel from the known prefix.** For each row, align the known prefix `CSSCTF` against ciphertext positions 0–5. Position `i` at tick `t` pins slot `(t + 43·i) mod 77` to the observed shift `cipher[i] - plain[i] (mod 26)`:

```python
PERIOD, STEP, KNOWN_PREFIX = 77, 43, 'CSSCTF'
base = epoch(train[0]['timestamp'])
wheel = {}
for row in train:
    tick = epoch(row['timestamp']) - base
    for index, plain in enumerate(KNOWN_PREFIX):
        slot = (tick + STEP * index) % PERIOD
        shift = (ord(row['ciphertext'][index]) - ord(plain)) % 26
        assert slot not in wheel or wheel[slot] == shift   # consistency check
        wheel[slot] = shift
assert len(wheel) == PERIOD      # all 77 slots recovered
```

The `assert` inside the loop is what proves the model: the same slot, reached from different rows, always yields the same shift.

**Step 2 — decrypt every row.** Walk each ciphertext, advancing the wheel index only on alphanumerics, and subtract the slot's shift (mod 26 for letters, mod 10 for digits):

```python
def decrypt(row):
    tick = epoch(row['timestamp']) - base
    index, result = 0, []
    for cipher in row['ciphertext']:
        slot = wheel[(tick + STEP * index) % PERIOD]
        if cipher.isupper():   result.append(chr((ord(cipher)-65-slot) % 26 + 65)); index += 1
        elif cipher.islower(): result.append(chr((ord(cipher)-97-slot) % 26 + 97)); index += 1
        elif cipher.isdigit(): result.append(str((int(cipher)-slot) % 10));          index += 1
        else:                  result.append(cipher)   # brace/underscore, no advance
    return ''.join(result)
```

**Step 3 — verify.** Decrypting all 60 training rows *and* all 60 validation rows (captured minutes later) yields one identical plaintext, which confirms the wheel is aligned to absolute UTC and not merely over-fit to one sample:

```console
$ python3 solve.py
Recovered 77 wheel slots; 60 training and 60 validation records agree.
CSSCTF{th3_cl0ck_r3m3mb3rs_3very_s3c0nd}
```

> Note: an early attempt advanced the wheel on *letters only* and produced plaintext that drifted after every digit. Counting digits as wheel positions (they consume a slot too) is what makes all rows agree — a useful reminder that "alphanumeric" includes the digits.

## Flag

```
CSSCTF{th3_cl0ck_r3m3mb3rs_3very_s3c0nd}
```

## Key takeaways

- A time-varying cipher is not automatically strong: if the plaintext is fixed and partly known, each timestamped sample leaks key material, and enough samples reconstruct the whole key schedule.
- The known flag prefix across consecutive ticks sweeps the full 77-slot wheel — one 60-second capture is sufficient; the second capture is only to prove absolute-time alignment.
- Period `77` and step `43` are coprime, so stepping by 43 visits every slot — that is exactly why a short known prefix covers the entire wheel.

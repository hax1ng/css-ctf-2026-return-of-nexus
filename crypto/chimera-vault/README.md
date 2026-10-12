# Chimera Vault

**Category:** Cryptography · **Points:** 65 · **Solves:** 232 · **Challenge ID:** 42

> The ancient custodians of the Chimera Vault didn't rely on standard asymmetric primitives to secure their root register.

## Challenge

A networked service with a downloadable source bundle:

```
Demodulate the carrier, trace the invariant through the matrix state
transitions, and invert the resonance to breach the vault.

Connection Information
- nc REMOTE_HOST:7334

Attachments
- chimera_vault.tar.gz   (server.py + Dockerfile, included here)
```

The prompt is a three-part recipe, and so is the service ([`server.py`](server.py)). You must clear all three phases in one 45-second connection to get the flag:

1. **Acoustic carrier synchronization** — decode a session token from a PCM audio burst.
2. **Non-commutative matrix drift telemetry** — observe a sequence of 3×3 matrices.
3. **Resonant knapsack intercept** — recover the exact 48-bit solution to a Merkle–Hellman knapsack.

## Initial analysis

The bundle extracts to a single Python service (no compiled target). Reading `server.py`, the central trick is that the **same secret multiplier `W` ties phases 2 and 3 together** — the matrix phase quietly leaks the private key of the knapsack phase. The three phases map directly onto the prompt's three verbs.

The solve was developed against a local build (`127.0.0.1:7867` with a test flag), which [`solve.py`](solve.py) recovered end to end before it was run against the authorized remote service.

### Phase 1 — the carrier

```python
f1 = 440 + (token & 0xFF) * 5
f2 = 1200 + ((token >> 8) & 0xFF) * 5
# 8000 Hz mono PCM, duration 0.8 s, two sine tones + light Gaussian noise
```

The session token (`0x1000 .. 0xEFFF`) is split into two bytes, each modulating one tone. The low byte sets a tone in `[440, 1715]` Hz, the high byte one in `[1200, 2475]` Hz, both in 5 Hz steps. With 6400 samples over 0.8 s the FFT bin width is `8000/6400 = 1.25` Hz, so the 5 Hz tone spacing is cleanly resolvable — an exact demodulation, no guessing.

### Phase 2 — the matrix drift

```python
d3 = (W - d1 - d2) % N
self.D = [[d1,0,0],[0,d2,0],[0,0,d3]]      # trace(D) = d1+d2+d3 = W (mod N)
...
def evolve_matrix(self):                    # M_{k+1} = M_k + D
    ...
```

The service prints `M_0 … M_3`. Because the diagonal drift matrix `D` has trace exactly `W mod N`, each step increases `trace(M_k)` by `W`. So the "invariant" the prompt mentions is:

```
W = (trace(M_1) - trace(M_0)) mod N
```

recoverable from the public matrices, and cross-checked against the other two transitions.

### Phase 3 — the knapsack

```python
self.r = [...]                      # superincreasing sequence, private
self.s = [(W * ri) % self.M_mod for ri in self.r]   # public weights
self.target_sum = sum(b*w for b,w in zip(self.target_bits, self.s))
```

This is a textbook **Merkle–Hellman knapsack**: public weights `s` are the superincreasing private weights `r` scaled by the modular multiplier `W (mod M_mod)`. Normally breaking it requires recovering `W`. Here phase 2 *hands you `W`* — the exact same value is reused as the knapsack multiplier.

## Vulnerability / core concept

**Key reuse across phases.** The scalar `W` is both the trace increment of the matrix drift (phase 2, fully observable) and the secret multiplier of the Merkle–Hellman knapsack (phase 3). Leaking `W` from the matrices turns the "hard" modular knapsack back into a trivial superincreasing one:

1. Recover `W` from `trace(M_1) - trace(M_0) (mod N)`.
2. Compute `W⁻¹ (mod M_mod)` and unscale the public weights to get the superincreasing private weights `r[i] = s[i]·W⁻¹ mod M_mod`.
3. Unscale the target, `residue = target_sum · W⁻¹ mod M_mod`, and greedily decode it against `r` (largest-first) to recover the exact bit vector.

Because `sum(r) < M_mod`, the modular reduction is a no-op on the real sum, so greedy decoding is exact.

## Exploitation

The full client is [`solve.py`](solve.py); run it as `python3 solve.py REMOTE_HOST 7334`. It drives all three phases over one socket.

**Demodulate the carrier.** Base64-decode the PCM, take the real FFT, and read off the two strongest bins, mapping each candidate tone frequency back to its byte:

```python
pcm = np.frombuffer(base64.b64decode(carrier_b64), dtype="<i2").astype(float)
spectrum = abs(np.fft.rfft(pcm))
freq_bins = {f: round(f * len(pcm) / 8000) for f in range(440, 2476, 5)}
peaks = sorted(freq_bins, key=lambda f: spectrum[freq_bins[f]], reverse=True)
observed = {f for f in peaks[:2] if spectrum[freq_bins[f]] > spectrum[freq_bins[peaks[0]]]/10}
# token = hi*256 + lo such that {440+5*lo, 1200+5*hi} == observed
```

If a carrier were ever intrinsically ambiguous the client reconnects rather than guess, but in practice the two tones pin the token uniquely.

**Trace the invariant and invert the resonance.** Parse `N`, `M_mod`, the four matrices, the public weights `S` and the target, then:

```python
traces = [sum(matrices[i][j][j] for j in range(3)) % n for i in range(4)]
w = (traces[1] - traces[0]) % n
assert all((traces[i+1] - traces[i]) % n == w for i in range(3))   # invariant holds

inverse = pow(w, -1, modulus)
private = [weight * inverse % modulus for weight in weights]        # superincreasing r
assert all(private[i] > sum(private[:i]) for i in range(48))

residue = target * inverse % modulus
bits = [0]*48
for i in reversed(range(48)):          # greedy largest-first decode
    if residue >= private[i]:
        bits[i] = 1
        residue -= private[i]
assert residue == 0
assert sum(b*w for b, w in zip(bits, weights)) == target            # re-check against public sum
```

Send the recovered token (hex) for phase 1 and the 48-bit string for phase 3. The service verifies both `check_sum == target_sum` **and** `user_bits == target_bits` (the greedy solution is the unique one), then prints the flag:

```console
$ python3 solve.py REMOTE_HOST 7334
Attempt 1: frequencies [...], token candidates ['0x....']
Recovered W=..., vector=0110...01
...
[+] RESONANCE EQUILIBRIUM ACHIEVED. OVERWRITING MASTER KEY...
[+] Flag: CSSCTF{tr4c3_1nv4r14nc3_4nd_4c0ust1c_sp3ctr4_7f9b8c}
```

## Flag

```
CSSCTF{tr4c3_1nv4r14nc3_4nd_4c0ust1c_sp3ctr4_7f9b8c}
```

## Key takeaways

- **Reusing one secret across two sub-systems collapses both.** The matrix trace increment and the Merkle–Hellman multiplier were the same `W`; observing the "harmless" matrix telemetry leaks the knapsack's private key.
- Merkle–Hellman knapsacks are only as strong as the secrecy of the modular multiplier — recover it and a superincreasing knapsack decodes greedily in linear time.
- FFT demodulation is exact when the signal is engineered for it: 0.8 s at 8 kHz gives 1.25 Hz bins, so 5 Hz-spaced tones recover the token byte-for-byte without brute force.
- The flag name itself spells out the intended path: *trace invariance* + *acoustic spectra*.

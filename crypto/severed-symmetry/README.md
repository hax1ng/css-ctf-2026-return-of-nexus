# Severed Symmetry

**Category:** Cryptography · **Points:** 200 · **Solves:** 274 · **Challenge ID:** 28

> Recover the access key hidden inside the intercepted archive before the Ætheric Order reclaims it.

## Challenge

> As the Kuiper Belt Relay reboots, your terminal intercepts an encrypted archive belonging to the Ætheric Order. Its contents survived The Severance, but the private key did not; only the encryption program, public equations, and ciphertext remain. The Order is already moving to reclaim it; recover the access key hidden inside before their secrets disappear into the Nexus again.

Attachments:

- `source.py` — the encryption program ([included](source.py)).
- `out.txt` — the public key (34 expanded polynomials) and the ciphertext (3 blocks), as JSON. **Omitted here for size** (see [Files](#files)).

No private key is given. This is a **multivariate public-key** scheme, and the whole challenge is a structural key-recovery.

## Initial analysis

[`source.py`](source.py) builds a multivariate encryption map over `GF(17)` with parameters `p=17, n=32, m=34, t=16, s=4`. Encryption of the flag is `P(x) = A1 · C(A2·x + b2) + b1`, a public map from 32 input variables to 34 output values, where the central map `C` has two layers:

- **Triangular quadratic layer (first `t = 16` coordinates).** `w[i] = z[i] − q_i(z[16:])`, with each `q_i` a random quadratic in the last 16 of the internal variables `z = A2·x + b2`. Each `w[i]` is degree-2 in `x`.
- **Unbalanced Oil-and-Vinegar layer (last `m − t = 18` coordinates).** `U_j` evaluated at `(w ‖ z[16:])`. Each `U_j` is a quadratic whose oil–oil products are suppressed: of the 16 trailing variables, **4 are vinegar and 12 are oil**, and oil never multiplies oil. Since `w` is already degree-2 in `x`, these 18 coordinates are **degree-4 in `x`**.

The two input/output affine maps `A1, A2` (with offsets `b1, b2`) are secret and hide this decomposition — the public polynomials are the fully expanded degree-4 forms, with no layer structure exposed. Breaking it means peeling the affine wrappers off using only the algebraic *shape* of the public equations.

The flag itself is framed into base-17 digits (`encode_frame`): a 4-byte big-endian length header plus the plaintext, two base-17 digits per byte, zero-padded to a multiple of `n = 32`, then each 32-digit block is encrypted as one input vector. Three ciphertext blocks → 96 digits → 48 bytes of frame.

## Vulnerability / core concept

The scheme leaks its own layering through **polynomial degree and Hessian rank**, and symmetric cryptanalysis recovers the hidden structure without ever finding `A1`/`A2` explicitly:

1. **The quartic coefficients betray the triangular layer.** Only the 18 OV coordinates reach degree 4; the 16 `w` coordinates are degree 2. So the 34×(quartic-monomials) coefficient matrix has a **16-dimensional left kernel** — 16 linear combinations of the public polynomials that cancel every degree-3/4 term and expose the degree-2 `w`-layer (up to an invertible output mix).
2. **Hessian radicals give the fiber lift.** The 16 recovered quadratics share a 16-dimensional common Hessian radical. Along it the `w`-coordinates move linearly and invertibly, so for each ciphertext block we can **lift** a 16-parameter family of inputs that all reproduce the block's `w`-values.
3. **The oil subspace is totally isotropic.** Restricting the 18 OV public coordinates to a fiber yields 18 quadratics in the 16 fiber parameters whose Hessians share a **12-dimensional common isotropic (oil) subspace** `O` — exactly the UOV weakness. The remaining 4 directions are vinegar.
4. **Guess 4 vinegar, solve 12 oil linearly.** Because oil never multiplies oil, fixing the 4 vinegar values makes all 18 equations **linear** in the 12 oil variables. Enumerating all `17⁴` vinegar assignments and solving the linear oil system yields **exactly one** preimage per ciphertext block.

Concatenate the three recovered input vectors, undo the framing, and read the flag.

## Exploitation

The attack is a four-stage pipeline. The structural/linear-algebra stages use SageMath; the `17⁴`-per-block vinegar search is a tiny C++ brute force. Heavy stages were run on the **kracken** compute host.

**Stage 1 — structural recovery ([`solve.py`](solve.py), run with `sage-run`).** It parses `out.txt`, builds the quartic-coefficient matrix, takes its 16-dim left kernel to recover the `w`-layer, computes the common Hessian radical, fixes the fiber-lift maps, interpolates each ciphertext fiber's 18 OV coordinates down to quadratics in 16 variables, and extracts the 12-dim oil subspace. The degree collapse is asserted explicitly:

```python
Wbasis = Q.left_kernel().basis_matrix()              # 16 combinations killing quartics
assert Wbasis.nrows() == 16
Wcoeff = np.mod(np.rint(wb @ coeff).astype(np.int64), P)
assert np.all(Wcoeff[:, degree >= 3] == 0)           # cubic terms vanish too → pure w-layer
...
assert all(np.all((O.T @ H[a] @ O) % P == 0) for a in range(18))   # oil is totally isotropic
```

It writes everything the brute force needs (`Hvv`, `Hvo`, and each block's `const`/`lv`/`lo`/`target`) to `prepared.json`.

```console
$ scp solve.py out.txt kracken:/tmp/ && ssh kracken 'cd /tmp && sage-run solve.py'
... recovered 16 quadratic outer coordinates
... oil dimension 12 found by Hessian kernels
... wrote prepared.json
```

**Stage 2 — flatten for C++ ([`make_numeric.py`](make_numeric.py)).** Converts `prepared.json` into a flat integer stream `numeric.txt`.

**Stage 3 — vinegar enumeration ([`solve_oil.cpp`](solve_oil.cpp)).** For each of the three blocks it tries all `17⁴ = 83 521` vinegar vectors; for each, the 18 equations become linear in the 12 oil variables, solved by GF(17) Gaussian elimination. It prints the unique consistent `(vinegar, oil)` per block:

```console
$ g++ -O2 -o solve_oil solve_oil.cpp && ./solve_oil
block 0 rank 12 vinegar 4 16 6 11 oil 7 14 8 16 9 9 5 16 12 11 2 1
block 1 rank 12 vinegar 4 14 12 0 oil 10 0 4 14 2 7 14 10 15 12 10 9
block 2 rank 12 vinegar 16 7 1 3 oil 15 3 14 13 7 6 0 0 5 6 5 4
block 0 solutions 1          # exactly one preimage per block
```

**Stage 4 — reconstruct, re-encrypt, decode ([`verify.py`](verify.py)).** It maps each `(vinegar, oil)` back through the vinegar/oil bases and the fiber lift to a full 32-digit input vector, **re-encrypts it with the original `source.py`** to confirm it reproduces the exact ciphertext block (an independent check that the recovery is correct), then concatenates the three vectors and runs `decode_frame` to strip the length header and base-17 framing:

```python
ct = encrypt_vector(archive['public_key'], x.tolist())
assert ct == archive['ciphertext']['blocks'][k]     # exact re-encryption match
...
plaintext = decode_frame(digits, p, 32)
print('UTF-8:', plaintext.decode('utf-8'))
```

```console
$ python3 verify.py
block 0 verified x = [...]
block 1 verified x = [...]
block 2 verified x = [...]
UTF-8: CSSCTF{P35T0_5CH3M3_4TT4CK2026}
```

All three blocks re-encrypt to the published ciphertext and decode to a valid UTF-8 flag, so the recovery is certain, not a guess.

## Flag

```
CSSCTF{P35T0_5CH3M3_4TT4CK2026}
```

## Files

Large inputs and solver-generated intermediates are **omitted** from this directory:

| File | Size | Why omitted |
|------|------|-------------|
| `out.txt` | 31M | Public key + ciphertext (JSON); exceeds the 2 MB limit. Regenerate by running `source.py`, or use the original challenge attachment. |
| `prepared.json` | 52K | Intermediate produced by `solve.py`. |
| `numeric.txt` | 8.0K | Intermediate produced by `make_numeric.py`. |

Committed: `source.py`, `solve.py`, `make_numeric.py`, `solve_oil.cpp`, `verify.py`.

## Key takeaways

- A multivariate scheme that composes a **triangular quadratic layer** with an **unbalanced Oil-and-Vinegar layer** leaks its structure through degree and Hessian rank — you never need to recover the secret affine maps directly.
- Degree separation (the `w`-layer stays degree 2 while the OV layer hits degree 4) hands you the outer coordinates as the **left kernel** of the quartic-coefficient matrix.
- The OV weakness is the **totally isotropic oil subspace**: once found, guessing the few vinegar variables linearises the system, so each ciphertext fiber has a single cheap preimage (`17⁴` guesses × a 12-variable linear solve).
- Always re-encrypt recovered preimages with the original program — an exact ciphertext match turns a plausible attack into a proof.

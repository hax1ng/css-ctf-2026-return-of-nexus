# prince walk

**Category:** Reverse Engineering · **Points:** 50 · **Solves:** 325 · **Challenge ID:** 46

> Your avatar starts at (1, 1), while the last surviving recovery beacon flickers as a distant star at (999999, 999999).

## Challenge

The channel opens into PRINCE WALK, an old planetary survey simulation damaged
by The Severance. Your avatar starts at `(1, 1)`, while the last surviving
recovery beacon flickers as a distant star at `(999999, 999999)`. Somewhere
beneath this impossible landscape lies the route back to the relay — you just
need to reach it.

Flag format: `CSSCTF{...}`

**Attachments**

- `prince_walk` — the challenge binary (~90 KB).

## Initial analysis

```
$ file prince_walk
prince_walk: ELF 64-bit LSB pie executable, x86-64, dynamically linked,
             interpreter /lib64/ld-linux-x86-64.so.2, stripped
```

Mitigations: PIE, NX, Full RELRO, canary (irrelevant for a rev challenge). The
binary is stripped.

It is a WASD walking simulator over **signed int32** coordinates, starting at
`(1,1)` with the beacon advertised at `(999999,999999)` = `(0xf423f, 0xf423f)`.
Working through it in Binary Ninja:

- `sub_4029ca` selects a **destination event** once both coordinates equal
  `0xf423f`. There are two routes in: the *standard* destination event (which
  sets a response bit), and a separate **"actually walked there"** event that
  requires **more than 1,999,995 WASD inputs** with no external coordinate
  tampering — the intended-but-infeasible legit path.
- When the standard destination response is displayed (after at least one
  input), `sub_4014c3` calls `sub_402c52`.
- `sub_402c52` takes the destination coordinates, runs an **8,320-instruction
  register VM** whose encrypted program sits in `.rodata` at file offset
  `0x4a80`, reconstructs a 128-byte buffer, validates length + printability + an
  **FNV-1a checksum**, and returns the text — which contains the flag.

## Vulnerability / core concept

The flag is **not stored as plaintext**; it is produced by a small
**coordinate-keyed virtual machine**. The VM's 16 registers and running `state`
are seeded from the destination coordinates (`X = Y = 999999`). Each of the
`0x2080` instructions is:

1. fetched from a **permuted** table index `j = (i*0xd9 + 0xcd6) % 0x2080`,
2. **decrypted** with a keystream derived from the running `state` via a
   splitmix-style `mix()` and golden-ratio constants (`0x9e3779b9`,
   `0x6a09e667`, …),
3. decoded into `op / dst / src1 / src2 / rotation`, and
4. executed by one of **8 opcodes** (`0xff` rotate-xor, `0xb3` bit-select,
   `0x8b` add-rotate, `0x83` **store**, `0x71` sub, `0x48`, `0x12` mix, `0x31`).

The store opcode `0x83` scatters one output byte each into a 128-byte buffer at
a position derived from the immediate. After all instructions run, `buf[0]` is a
length, `buf[1:1+len]` is the message body, and the four bytes after it are an
FNV-1a checksum over the body. Reproduce the VM with the correct coordinates and
you recover the flag; the checksum is a built-in correctness oracle.

So the solve never touches the game: just **emulate the VM offline** with
`X = Y = 999999` and read out the message.

## Exploitation

`solve.py` is a deterministic, self-contained emulator that reads the encrypted
instruction table out of the attachment itself:

- Reads `0x2080` table entries of two 32-bit words each from file offset
  `0x4a80`.
- Seeds the registers and state from the coordinates:

  ```python
  regs  = [mix(((i+1)*0x9e3779b9) ^ X ^ rol(Y, i+1)) for i in range(16)]
  state = mix((rol(Y, 0x13) + X) ^ 0xa4093822)   # X = Y = 999999
  ```

- For each instruction `i`: de-permute to `j`, decrypt `word`/`imm` against the
  keystream, decode, execute the matching opcode, store output bytes on `0x83`,
  and advance `state`.
- After `0x2080` steps all 128 positions are written. It then reads
  `length = output[0]`, `body = output[1:1+length]`, and verifies
  `FNV-1a(body)` against the stored 4-byte checksum.

Result: a 72-byte message ending in the flag, with computed FNV-1a `0x763cc96c`
matching the embedded `0x763cc96c`.

```
$ python3 solve.py        # reads prince_walk from the same directory
length 72 fnv 0x763cc96c stored 0x763cc96c
...CSSCTF{P12INC3_0R_P1NC3?}
```

## Flag

```
CSSCTF{P12INC3_0R_P1NC3?}
```

## Key takeaways

- The "impossible" `(999999,999999)` target and ~2M-input legit walk are
  misdirection: the flag is **derived by a coordinate-keyed VM**, not by
  physically reaching the beacon.
- Recognise an embedded register VM (fetch → decrypt → dispatch loop over a
  `.rodata` table) and just reimplement it. A built-in FNV-1a checksum doubles
  as a free "did I get it right?" oracle.
- `mix()` (splitmix finalizer), golden-ratio `0x9e3779b9`, and FNV constants
  (`0x811c9dc5` / `0x1000193`) are tell-tale fingerprints when reversing custom
  obfuscation.

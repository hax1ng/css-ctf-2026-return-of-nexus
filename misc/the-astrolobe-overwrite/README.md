# The Astrolobe Overwrite

**Category:** Misc · **Points:** 250 · **Solves:** 162 · **Challenge ID:** 6

> Feed a self-rewriting bytecode VM a program that reaches "harmonic resonance" across three rings — a permutation gate, a coupled recurrence, and an elliptic curve — while landing inside a tight execution-cycle window.

## Challenge

> When "The Severance" hit in 2100, the Kuiper Relay wasn't abandoned. Instead, it was locked into a loop governed by the Council. To prevent manual takeover, the council's instruction consumes and rewrites its own memory.
>
> To force an administrative override, your payload must achieve harmonic resonance across the three rings of the Astrolabe:
> 1. Unravel the permutation field of the first gate.
> 2. Stabilize the coupled wave recurrence across the lattice.
> 3. Lock onto the projective coordinates of the orbital horizon.
>
> The telemetry receiver requires exact synchronization with the beacon and will purge the core if total execution falls outside the quantum decay window.
>
> Flag Format: CSSCTF{...}

**Connection:** `nc REMOTE_HOST 7654`
**Attachments:** `ouroboros.7z` (included) — a stripped 64-bit PIE ELF plus its Dockerfile and a placeholder `flag.txt`.

## Initial analysis

Extract `ouroboros.7z` and triage the binary:

```bash
7z x ouroboros.7z
file ouroboros/ouroboros   # ELF 64-bit LSB PIE, stripped
```

Build and run the supplied Dockerfile locally (the included `flag.txt` is only a placeholder) so the service can be driven safely on `127.0.0.1:17654` before touching the authorized remote.

Reversing the ELF (Binary Ninja over MCP) reveals a tiny **bytecode virtual machine** whose defining trait matches the "Ouroboros" theme — *it consumes and rewrites its own instruction stream as it runs*:

- It reads up to **512 bytecode bytes** from the client (hex-encoded).
- Four **16-bit registers**.
- Each instruction is 4 bytes: `opcode_token, dst, hi, lo`.
- A **rolling XOR key**: the real opcode is recovered as `table.index(opcode) ^ (key & 7)`, and after each instruction the key advances as `key = (key*31 + (R0 & 0xff)) & 0xff`.
- An **eight-entry opcode permutation table** that swaps two entries (indexed by `R0 & 7` and `R1 & 7`) after every ordinary instruction — so the encoding of the *same* opcode changes as the program executes.
- A final-check opcode (`0x7f`) that must fire while the total cycle count sits in the **112–128 window** ("quantum decay window").

## Vulnerability / core concept

There is no memory-corruption bug; the challenge is to **author a valid self-modifying program** that drives the four registers to one exact state and trips the final check in time. The final check (the "three rings"):

1. **Beacon sync.** A time-based beacon `BEACON = (time() / 30) % 65521` is printed in the banner and subtracted from every register (mod `P = 65521`) before the maths. So whatever target state the maths needs, we must *load `(target_i - … )`* relative to the live beacon.
2. **Permutation field (ring 1).** Each post-beacon register is run through a non-linear permutation `F`:
   ```
   F(a): b = (a ^ 0x5aa5) mod P;  q = b^17 mod P;  q = rotate16(q, 7);  return (q ^ 0x1337) mod P
   ```
3. **Coupled wave recurrence (ring 2).** The four transformed values must satisfy four coupled recurrence equations tying each register to the next with the constants `40414, 12506, 4535, 39941` (mod `P`).
4. **Orbital horizon (ring 3).** Two of the values must additionally be points on the elliptic curve `y² = x³ + 17x + 43  (mod 65521)`.

Rings 2 and 3 together form a simultaneous system over GF(65521). Solving it is the only hard compute in the challenge, so it is offloaded to **kracken**.

## Exploitation

**Step 1 — solve the register system (offline, on kracken).** `solve_math.cpp` precomputes the field tables (`F`, squares, curve values, modular inverses), enumerates all curve points, and brute-forces the coupled recurrence + curve constraints across 20 threads:

```bash
scp solve_math.cpp kracken:/tmp/
ssh kracken 'g++ -O3 -pthread /tmp/solve_math.cpp -o /tmp/solve_math && /tmp/solve_math'
```

It finds the unique consistent state:

- post-transform register values `F(·)` = `(37101, 35947, 43627, 40060)`
- the **pre-transform** registers that produce them = `(1, 218, 59611, 783)`

So after the beacon is subtracted, each register must equal its pre-transform value. The register we load is therefore `(pre_i + beacon) mod P`.

**Step 2 — build the self-modifying program (`solve.py`).** The solver re-implements the VM's encoder so that each emitted byte is correct *given the current rolling key and permutation table*:

- Emit four `0x10` (load-immediate) instructions setting registers to `(pre_i + beacon) mod P`, in order `(1, 2, 3, 0)` (R0 last so the key/table evolution is predictable).
- Emit **98** `0x20` (`MOV R1,R1`) no-op cycles, then the final-check opcode `0x7f`. Four loads + 98 moves + the ten cycles of the final instruction = **exactly 112** cycles — the minimum of the decay window.
- Each `emit()` applies the same `key`/`table` updates the VM will, so the on-the-wire opcode tokens decode back to the intended opcodes. The resulting program is **412 bytes**, under the 512 limit.

**Step 3 — synchronize and fire.** Connect, read the banner, parse `BEACON: 0x....`, build the beacon-specific program, and send it hex-encoded:

```bash
python3 solve.py remote      # or `python3 solve.py local` against the Docker build
```

The service reports stabilization across all three rings and returns the flag.

## Flag

```
CSSCTF{0ur0b0r0s_g00d_j0b_b01s_heh3_67}
```

## Key takeaways

- "Consumes and rewrites its own memory" is a literal spec: the rolling XOR key + swapping opcode table mean the encoder must simulate VM state to emit each byte correctly.
- Decompose the flavor text — permutation gate, coupled recurrence, elliptic curve — into the three independent constraints of the final check.
- The register system over GF(65521) is the only heavy step; enumerate curve points and brute-force it on kracken, then keep the live part (beacon sync + program encoding) light and exact.
- Watch the "quantum decay window": pad with no-op cycles to land the final instruction at exactly 112 total cycles.

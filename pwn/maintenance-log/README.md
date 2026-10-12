# Maintenance Log

**Category:** Pwn · **Points:** 50 · **Solves:** 265 · **Challenge ID:** 49

> The vendor insists their service is fortified with stack canaries… but the interface IS LEAKING.

## Challenge

Our diagnostics terminal logged an anomaly during maintenance. The vendor
insists their service is fortified with stack canaries and safe from memory
corruption, but the interface IS LEAKING. Can you forge a maintenance report,
bypass the perimeter, and acquire administrative clearance?

Flag format: `CSSCTF{...}` · Remote: `nc REMOTE_HOST 7312`

**Attachments** — `sector01_handout.zip` containing:

- `chall` — the challenge binary (~14 KB), included here.
- `Dockerfile` — the deployment (socat `TCP-LISTEN:7312,fork EXEC:./chall`), included here.
- `flag.txt` — a **decoy** flag shipped in the handout; **not** the live flag and
  intentionally omitted from this writeup.

## Initial analysis

```
$ file chall
chall: ELF 64-bit LSB executable, x86-64, dynamically linked,
       interpreter /lib64/ld-linux-x86-64.so.2, stripped
```

Mitigations (via `readelf`): **No PIE** (`ET_EXEC` → fixed gadget/win
addresses), NX enabled, **stack canary present** (exactly as the prompt brags),
Partial RELRO. The binary is stripped, so functions are referenced by address.

Three functions matter:

- `sub_40139a` (**report step**) — prints
  `Report buffer allocated at: 0x...`, **leaking the stack address** of its
  `0x50`-byte report buffer, then `read(0, buf, 0x50)`. It fills exactly `0x50`
  bytes, so it does not overflow its own frame.
- `sub_401348` (**operator step**) — `read(0, operator_buf, 0x21)` into a
  `0x20`-byte buffer: a **single-byte overflow** that overwrites **only the low
  byte of a saved RBP**.
- `sub_401268` (**win**) — opens and prints `flag.txt` when called with
  `EDI = 0xdeadbeef` and `ESI = 0xcafebabe`.

## Vulnerability / core concept

A **leaked stack pointer + a one-byte saved-RBP overwrite → stack pivot** into
attacker-controlled data, which **never touches the canary**. The vendor's
canary is real but irrelevant: we don't smash past it.

The operator off-by-one rewrites the least-significant byte of the saved RBP
that the report function restores. When the report function runs `leave; ret`,
`RBP` is reloaded from the corrupted slot and `RSP` pivots to it — landing
inside the `0x50` report buffer we already filled with a ROP chain. The leak of
the buffer address is what makes the single controllable byte deterministic: the
original saved RBP is `buf + 0x50`, and changing only its low byte can only move
it within its own 256-byte window.

## Exploitation

`exploit.py` implements the full sequence (connecting only to the local Docker
build by default, or to a human-confirmed endpoint with `--remote`):

1. **Leak.** Parse `Report buffer allocated at: 0xADDR`. The original saved RBP
   is `saved_rbp = buf + 0x50`.
2. **Pick the pivot.** `pivot = max(buf, saved_rbp & ~0xff)` — the 256-byte-aligned
   slot at or below the saved RBP but still inside our buffer. Because only the
   low byte is controllable, the pivot must share the upper 56 bits of
   `saved_rbp`.
3. **Stage the chain** at `offset = pivot - buf` inside the `0x50` buffer. The
   7-qword (56-byte) chain calls `win` with the right arguments:

   ```
   [pivot+0x00]  0x0000000000000000   <- consumed by `pop rbp` inside `leave`
   [pivot+0x08]  pop rdi; ret  0x40124d
   [pivot+0x10]  0xdeadbeef
   [pivot+0x18]  pop rsi; ret  0x40124f
   [pivot+0x20]  0xcafebabe
   [pivot+0x28]  ret           0x401016   # 16-byte stack alignment before the call
   [pivot+0x30]  win           0x401268
   ```

   If `offset + 56 > 0x50`, this connection's (ASLR-dependent) low byte leaves no
   room for the whole chain, so `exploit.py` reconnects and retries (`--tries`,
   default 8) until a layout fits. The report buffer is sent as
   `b"A"*offset + chain`, padded out to `0x50`.
4. **Trigger.** Send the operator overflow `b"C"*0x20 + bytes([pivot & 0xff])`:
   the 33rd byte rewrites the saved-RBP low byte. On return, `leave; ret` pivots
   into the buffer, the chain runs, and `win()` prints the flag.

The supplied `Dockerfile` was built and run locally on `127.0.0.1:17312`, where
the exploit produced the access-granted message and the decoy flag. After a
human confirmed the team endpoint, the same exploit against `REMOTE_HOST:7312`
returned the real flag below.

## Flag

```
CSSCTF{Duh_m4t3_1_4m_sl33py}
```

## Key takeaways

- A pointer leak plus a **single-byte saved-RBP overwrite** is enough to pivot
  the stack into attacker data — the canary never comes into play.
- `leave; ret` is a pivot primitive: control the saved RBP and you control RSP
  on the next return. The first qword at the pivot is eaten by the `pop rbp`
  inside `leave`, so the chain proper starts at `pivot + 8`.
- No-PIE fixes the gadget and win addresses; only the stack is randomized, and
  the leak hands that to you. Keep the chain short and retry across connections
  since the usable offset depends on the ASLR'd low byte.
- The handout `flag.txt` is a decoy — the real flag only comes from the live win
  path.

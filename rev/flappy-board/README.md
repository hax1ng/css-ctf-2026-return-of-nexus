# FLAPPY BOARD

**Category:** Reverse Engineering · **Points:** 80 · **Solves:** 221 · **Challenge ID:** 27

> Guide it through three relay sectors before your twenty-minute connection expires, and recover the access key.

## Challenge

The beacon reveals a stranded Polaris courier drone carrying a Nexus
restoration packet. Its flight console, FLAPPY BOARD, still works, but corrupted
departure timers hold it grounded and its controls change after every
checkpoint. Guide it through three relay sectors before your twenty-minute
connection expires, and recover the access key before the factions seal the
channel.

Flag format: `CSSCTF{...}`

**Attachments**

- `flappy_board` — the game client (~43 KB). *(The binary's embedded backend
  host string has been redacted to the placeholder `REMOTE_HOST_`; it originally
  pointed at the event's ephemeral instance IP.)*

## Initial analysis

```
$ file flappy_board
flappy_board: ELF 64-bit LSB pie executable, x86-64, dynamically linked,
              interpreter /lib64/ld-linux-x86-64.so.2, stripped
```

Mitigations: PIE, NX, Full RELRO, canary. The binary is an **X11 + libcurl
game client** — a Flappy-Bird clone — not a self-contained flag checker. There
is **no `CSSCTF` string anywhere in it**, and the flag display buffer at
`0x417080` has only two references: `sub_405032` writes a decoded `flag` form
field into it, and `sub_402ec2` draws it. There is no local flag generator — the
flag only ever arrives from the server's round-4 response.

The client talks to a backend over HTTP (default base
`http://REMOTE_HOST:8765`). Responses are **URL-encoded form data**
(`key=value&…`), **not JSON** — `sub_403e4a` parses named fields, turns `+` into
space, and percent-decodes with `curl_easy_unescape`. The protocol, reversed
from the client:

```
POST /api/attempt   (empty)  -> token=<64>&round=1&target=10
GET  /api/attempt            -> round & seed & target & wait_seconds & remaining_seconds
POST /api/complete  round=&wait_ms=<ws*1000>&ticks=&score=&flaps=i0,i1,...
                             -> next round params, or round=4&flag=CSSCTF{...}
```

A **practice oracle** (`/api/practice`, `/api/practice/check`) validates physics
server-side without spending a scored round.

The game physics (transcribed from `sub_406c0f` init, `sub_406cfe` step,
`sub_406bc6` gap RNG, `sub_406b88` xorshift32):

- **xorshift32** PRNG (shifts 13 / 17 / 5), seeded with `seed or 1`.
- bird `y` starts `0xf000`; a flap sets `vel = -0x6bc`; gravity adds `+0x43`/tick
  capped at terminal `+0x800`; five pipes scroll `-0x2cd`/tick; a pipe gap is
  `rng % 0xe7 + 0x7d`.
- death on floor/ceiling (`y <= 0xc00` or `y > 0x1d3ff`) or pipe collision;
  score increments as pipes pass; tick cap `0x8c9f`.
- The submitted replay carries **only the flap tick indices**; the server
  re-simulates them.

## Vulnerability / core concept

This is a **protocol-reversing + deterministic-simulation** challenge. The
server hands out a `seed` per round; the client must play to the target score
(10 / 20 / 30 across rounds 1–3) and submit the exact flap tick indices. Because
the physics and RNG are fully deterministic and transcribed from the binary, you
can **solve each seed offline**, skip the GUI and the client-side "corrupted
departure timer" waits entirely, and submit perfect replays. Round 4's response
carries the flag.

## Exploitation

Three committed scripts, no network required to understand them:

- **`flappy_engine.py`** — faithful transcription of init / step / RNG, plus a
  per-seed solver: a fast greedy threshold + look-ahead sweep (`solve_greedy`)
  with a **beam-search fallback** (`solve_beam`, widths up to 3000) for stubborn
  seeds, and `verify_replay()` that re-simulates the exact flap list the way the
  server will. Its self-test solves ~100% of random seeds.
- **`replay_solver.py`** — standalone offline simulator + adaptive scheduler;
  `--form` emits the exact `/api/complete` body for a given seed/round/wait.
- **`solve.py`** — the automated client. `new_attempt` → read round params → for
  each round `solve_seed(seed, target)`, verify, then
  `POST /api/complete` with `wait_ms = wait_seconds * 1000` and the
  comma-separated flap indices → repeat rounds 1–3 → round 4 returns the flag.
  Network access is gated behind `--go` and an authorized endpoint.

Two gotchas that decided success:

- **`wait_seconds` (180 / 360 / 600) are purely client-side delays.** The server
  accepts a correctly-formed replay immediately as long as the body carries
  `wait_ms = wait_seconds * 1000`; there is no need to actually wait out the
  twenty-minute "timer".
- **No trailing newline in the form body.** A newline after the final flap index
  produces `Invalid flap replay`.

After the service URL was supplied (authorizing live testing), the offline
scheduler passed the practice check, then completed rounds 1, 2, and 3 against
`/api/complete`, and the round-4 response returned the flag.

## Flag

```
CSSCTF{birdddd}
```

## Key takeaways

- When a game client submits a **replay** to a server that re-simulates it,
  reverse the physics + RNG exactly and you can generate optimal replays
  offline — no GUI, no real-time play.
- Read the wire format: this server speaks `x-www-form-urlencoded`, and a stray
  trailing newline in the body is rejected.
- Client-side "timers" are often just that — the server validated replays
  instantly regardless of the advertised wait.
- The flag lived only in the server's round-4 response; the binary is pure
  transport/physics, so static string hunting (including single-byte-XOR scans)
  was a dead end.

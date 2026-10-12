# CSS CTF 2026: Return of Nexus

Solutions, writeups, and solve scripts for **CSS CTF 2026: Return of Nexus**, an
online jeopardy CTF run by the **University of Sydney Cybersecurity Society (CSS)**
on a CTFd scoreboard at `ctf.cybersecurity.sydney`.

- **Event:** CSS CTF 2026: Return of Nexus (jeopardy, online)
- **Dates:** 30 September – 2 October 2026 (AEST)
- **Player:** [`hax1ng`](https://github.com/hax1ng)
- **Solved:** 23 challenges · **1,749 points**

The event was themed around the *Return of Nexus* storyline — the Quantum Nexus
Network rebooting after "The Severance," with the recurring **KBR-17 Kuiper Belt
Relay** tying the forensics and pwn tracks together. Challenges spanned crypto,
web, pwn, rev, forensics, stego, OSINT, misc, and hardware.

Each challenge has its own directory containing a polished `README.md` writeup
plus the final solve scripts / exploits / relevant source. Oversized or
reproducible challenge inputs (disk images, long WAV captures, multi-MB map
archives) are **not** committed to keep the repo lightweight — they are
described in the relevant writeup instead.

## Solved challenges

### crypto

| Challenge | Points | Solves | Writeup |
|-----------|-------:|-------:|---------|
| Chrono I | 25 | 552 | [writeup](crypto/chrono-i/) |
| Chimera Vault | 65 | 232 | [writeup](crypto/chimera-vault/) |
| Chrono II | 100 | 385 | [writeup](crypto/chrono-ii/) |
| Severed Symmetry | 200 | 274 | [writeup](crypto/severed-symmetry/) |

### forensics

| Challenge | Points | Solves | Writeup |
|-----------|-------:|-------:|---------|
| Echoes of the Relay | 33 | 361 | [writeup](forensics/echoes-of-the-relay/) |
| The False Timeline | 66 | 431 | [writeup](forensics/the-false-timeline/) |
| Signal Fracture | 100 | 401 | [writeup](forensics/signal-fracture/) |
| Ghost Frequency | 115 | 364 | [writeup](forensics/ghost-frequency/) |

### hardware

| Challenge | Points | Solves | Writeup |
|-----------|-------:|-------:|---------|
| Lamp Drill | 15 | 497 | [writeup](hardware/lamp-drill/) |
| Silicon Snare | 250 | 355 | [writeup](hardware/silicon-snare/) |

### misc

| Challenge | Points | Solves | Writeup |
|-----------|-------:|-------:|---------|
| A Star Trail 1 | 20 | 421 | [writeup](misc/a-star-trail-1/) |
| A Star Trail 2 | 75 | 350 | [writeup](misc/a-star-trail-2/) |
| A Star Trail 3 | 120 | 206 | [writeup](misc/a-star-trail-3/) |
| The Astrolobe Overwrite | 250 | 162 | [writeup](misc/the-astrolobe-overwrite/) |

### osint

| Challenge | Points | Solves | Writeup |
|-----------|-------:|-------:|---------|
| Dead Faction Servers | 10 | 349 | [writeup](osint/dead-faction-servers/) |
| 2(-1) Senses | 30 | 258 | [writeup](osint/2-1-senses/) |

### pwn

| Challenge | Points | Solves | Writeup |
|-----------|-------:|-------:|---------|
| Dockside Ticket Office | 25 | 348 | [writeup](pwn/dockside-ticket-office/) |
| Maintenance Log | 50 | 265 | [writeup](pwn/maintenance-log/) |

### rev

| Challenge | Points | Solves | Writeup |
|-----------|-------:|-------:|---------|
| prince walk | 50 | 325 | [writeup](rev/prince-walk/) |
| FLAPPY BOARD | 80 | 221 | [writeup](rev/flappy-board/) |

### stego

| Challenge | Points | Solves | Writeup |
|-----------|-------:|-------:|---------|
| Colour Shift | 45 | 434 | [writeup](stego/colour-shift/) |

### web

| Challenge | Points | Solves | Writeup |
|-----------|-------:|-------:|---------|
| Welcome to Star City | 15 | 591 | [writeup](web/welcome-to-star-city/) |

### welcome

| Challenge | Points | Solves | Writeup |
|-----------|-------:|-------:|---------|
| Welcome to Nexus | 10 | 749 | [writeup](welcome/welcome-to-nexus/) |

## Notable challenges

- **The Astrolobe Overwrite** (misc, 250 pts, 162 solves) — the lowest-solve
  challenge in this set; an `ouroboros` self-referential puzzle solved with a
  supporting C routine.
- **Silicon Snare** (hardware, 250 pts) — recovering a bitstring by tracing a
  gate-level schematic exported as SVG and reconstructing the shift-register
  logic programmatically.
- **Severed Symmetry** (crypto, 200 pts) — a multivariate ("pesto"/oil-and-
  vinegar style) scheme attack, with the heavy linear-algebra step dropped to C.
- **The Chrono series** (crypto) — time-as-the-key puzzles where the encryption
  seed is derived from a timestamp, escalating from an offline cipher (Chrono I)
  to a remote timing/PRNG recovery (Chrono II).

## Flag format

```
CSSCTF{...}
```

## Layout

```
<category>/<challenge-name>/
  README.md     # writeup
  solve.*       # final solve script / exploit
  ...           # relevant source or small target binaries
```

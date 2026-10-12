# Silicon Snare

**Category:** Hardware · **Points:** 250 · **Solves:** 355 · **Challenge ID:** 31

> Trace the signal paths through the gates and find the one 32-bit input pattern that drives the centre node, Override, to logic high.

## Challenge

> The Kuiper Belt relay fail-safe is a hardwired optical routing matrix.
>
> Thanks to the bravery of a specific R2-series astromech droid, you have been provided
> the original schematic for its layout and proprietary analogue logic nodes. Trace the
> signal paths through the gates and find the one 32-bit input pattern that drives the
> centre node, Override, to logic high (1).
>
> * Software won't help you much here. The only thing to follow is the wire.
> * Some wires will intentionally overlap to hinder your efforts. Thankfully, you have
>   its SVG; it will let you zoom in infinitely to inspect for detail.
>
> Submit `CSSCTF{…}`. Inside the braces, enter 32 bits (1s and 0s) with no spaces.
> I00, at 12 o'clock, is the first bit. Read clockwise through I31.

Attachments:

- `schematic.svg`
- `schematic.png` (omitted here for size — see **Files**)

## Initial analysis

The two attachments are byte-identical images of a single Matplotlib-rendered circuit:
32 inputs `I00..I31` arranged clockwise around the rim, a ring of outer gates, several
layers of inner gates, and a central `Override` node. The legend assigns each gate a
one-letter prefix:

- `m` = **XOR** (Merge)
- `f` = **AND**
- `n` = **NOT**
- `s` = **Shift** (a 2-in / 2-out cell — see below)

The prompt insists that *"software won't help you much"*, and for a human that is true:
the intended path is to zoom the SVG and trace every wire by eye, defeating deliberate
crossing/overlap decoys. But the SVG is structured data, so the tracing itself can be
mechanised without "solving" anything — the puzzle is entirely in reading the wires
correctly.

## Vulnerability / core concept

The circuit is a fixed combinational netlist. Recovering the flag is two separate jobs:

1. **Transcribe** the schematic into a gate-level netlist (who feeds whom).
2. **Invert** it: find the input `I00..I31` making `Override = 1`.

Step 2 is trivial once step 1 is correct — it is a Boolean-satisfiability problem over
32 variables. All the difficulty (and all the decoys) live in step 1, the tracing.

### Reading the SVG

`parse_svg.py` loads `schematic.svg` with `lxml`, pulls every `line2d_*` path and every
`text_*` gate label, and records each wire's two endpoints plus the nearest gate labels:

```python
paths[i] = {'start': (x0,y0), 'end': (x1,y1), 'color': '#rrggbb', ...}
# near(pt) -> the three closest gate labels, e.g. "m00:8.2,m1f:45.3,m01:51.7"
```

Its dump (committed as `paths.txt`) is what makes manual tracing tractable: crossings
that are *not* marked with a filled junction dot are **not** joins, so each coloured
path can be followed from a known endpoint to a known gate. `make_gates.py` additionally
crops each shift cell out of the raster and rings its wired pins, used to classify the
shift gates by eye.

### The gate incidence

From the traced endpoints:

- Paths 1–64 feed the 32 outer XOR (`m`) gates: `m_i = I_i XOR I_(i+7 mod 32)`.
- Paths 139/140 also route `I03` and `I01` directly into AND gate `f12`.
- The remaining paths wire the inner `f`/`n`/`s` gates through to `Override` (path 143).

The **shift** cells are the subtle part. Each `s` gate has a pointed A/Y0 side and a flat
B/Y1 side; only one of its two outputs is actually wired. Classifying A vs. B (using the
zoomed `shift_gates_close.png` inspection montage) gives, per cell, either
`Y0 = A OR B` or `Y1 = A AND NOT B`. Those choices are recorded in the `shift` table of
`solve.py`.

## Exploitation

`solve.py` encodes the exact traced netlist in Z3 — the `end`/`start` dictionaries are
the per-path source/sink gate for every wire, straight from the tracing — and asserts
`Override = 1`:

```python
for i in range(32):
    s.add(ws[2*i+1] == xs[(i+7) % 32])   # outer XOR inputs
    s.add(ws[2*i+2] == xs[i])
...
val = Xor(...)          # m = XOR
val = And(...)          # f = AND
val = Not(...)          # n = NOT
val = Or(A,B) if y==0 else And(A, Not(B))   # s = shift, wired output only
...
s.add(ws[143])          # Override high
```

Running it recovers the bitstring and then proves it is the **only** solution by
re-checking with that assignment excluded:

```console
$ python3 solve.py
SAT: sat
01010000010000010101001101010011
ones [1, 3, 9, 15, 17, 19, 22, 23, 25, 27, 30, 31]
second? unsat
```

`second? unsat` means no other 32-bit input drives `Override` high — the transcription
yields a unique answer, which is the strongest check that the tracing was done right.

As a sanity cherry on top, the 32-bit pattern is ASCII:

```
01010000 01000001 01010011 01010011  ->  0x50 0x41 0x53 0x53  ->  "PASS"
```

Reading `I00` first (12 o'clock) and clockwise through `I31` gives the flag body.

## Flag

```
CSSCTF{01010000010000010101001101010011}
```

## Key takeaways

- An SVG schematic is structured data: you can extract wire endpoints and gate labels programmatically to trace a "no software allowed" circuit *mechanically* without shortcutting the actual puzzle.
- Unmarked crossings are decoys — only filled junction dots are real joins.
- The 2-out shift cells only wire one output; getting A/B orientation right per cell is the make-or-break detail.
- Encode the netlist in Z3 and re-check for a second model: `UNSAT` the second time proves both the answer and that your transcription is self-consistent.

## Files

- `schematic.svg` (968K) — committed; zoom losslessly to inspect wire crossings.
- `schematic.png` (1.9M) — **omitted for size**; identical content to the SVG.
- Solver-generated inspection montages (`shift_gates_montage.png`, `shift_gates_close.png`, `shift_gates_annotated.png`) are **omitted**; regenerate with `make_gates.py` from the full-res `schematic.png`.

# Lamp Drill

**Category:** Hardware · **Points:** 15 · **Solves:** 497 · **Challenge ID:** 35

> Warm-up. No spaces.

## Challenge

A single-image warm-up for the hardware / reverse-engineering track. The prompt is
just:

> Warm-up. No spaces.
>
> Flag Format: CSSCTF{...}

Attachments (the same diagram in two formats):

- `lampDrill.png`
- `lampDrill.svg`

## Initial analysis

The image is a logic-gate drill drawn as rows of "lamps". Each lamp is either
**filled** (●) or **hollow** (○). At the top sits a four-case legend that is really a
truth table:

| inputs | output |
|--------|--------|
| ● ● | ● |
| ● ○ | ○ |
| ○ ● | ○ |
| ○ ○ | ○ |

Treating filled = `1` and hollow = `0`, the output is `1` only when **both** inputs
are `1`. That is a two-input **AND** gate.

Below the legend are 24 boxed lamp **pairs**, laid out in 3 rows of 8. Each pair is one
AND evaluation producing a single bit; eight pairs per row make an 8-bit byte, so each
row decodes to one ASCII character. "No spaces" tells us the three bytes concatenate
directly.

## Vulnerability / core concept

Pure gate-reading: apply `AND` to each lamp pair, read the 8 result bits of each row
MSB-first as a byte, and convert to ASCII.

## Exploitation

Reading the boxes left-to-right, top-to-bottom and ANDing each pair:

| Row | Input pairs (●=1 ○=0) | Output bits | Byte | ASCII |
|-----|-----------------------|-------------|------|-------|
| 1 | `10 11 11 01 00 10 11 11` | `01100011` | `0x63` | `c` |
| 2 | `01 11 11 11 10 01 11 11` | `01110011` | `0x73` | `s` |
| 3 | `00 11 11 11 10 01 11 11` | `01110011` | `0x73` | `s` |

The three bytes spell `css`, which drops straight into the flag braces.

No script is required — the whole solve is reading the diagram — but the committed
`lampDrill.svg` is handy because it zooms losslessly to confirm each lamp's fill state.

## Flag

```
CSSCTF{css}
```

## Key takeaways

- Read the legend first: here it is a disguised truth table that pins the gate down as AND.
- "No spaces" and a 3×8 lamp layout quietly tell you the output is three concatenated ASCII bytes.
- Filled/hollow → `1`/`0` and MSB-first byte grouping is the standard decode for these lamp-drill puzzles.

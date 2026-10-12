# A Star Trail 1

**Category:** Misc · **Points:** 20 · **Solves:** 421 · **Challenge ID:** 22

> Pilot a Very Important Package from Earth to Lancer-RXKRD in under 25 days, following only the mapped interplanetary routes.

## Challenge

> (You may have seen this last year)
>
> Polaris Logistics has an urgent delivery that needs to be transported across the star system. As the pilot of this V.I.P. (Very Important Package), you need to begin planning your trip from *Earth* to *Lancer-RXKRD* immediately. Remember to follow company protocol; you *have* to follow the designated paths between planet/oids to comply with interplanetary law. If you can't deliver the V.I.P. in under 25 days, you might as well forget about your end of year bonus.
>
> \- Polaris Logistics.
>
> Submit your flag using the by combining the first character of each planet/oid in your path together and then adding the number of days your path takes (with 1 decimal place) onto the end, separated by a dash. E.g. if your path from A-PLANET TO B-PLANET was PAPA, OSCAR, SIERRA, TANGO, 2025PLANET and took exactly 5 days, the flag would be `CSSCTF{POST2-5.0}`

**Attachments:** `A_Star_Trail.png` (3780×1890 PNG star map, included here).

## Initial analysis

The attachment is a single image of a star map. There is no binary or service — the whole puzzle is reading the map. Running `file` confirms a plain PNG; `strings`/`exiftool` reveal nothing hidden. The picture is a **weighted, undirected route graph**: nodes are planet/oids, dashed edges connect neighbours, and each edge is labelled with a travel time in days.

The only work is to transcribe every edge and its weight, then find the shortest Earth → Lancer-RXKRD route. The transcription lives in `solve.py` as an edge list.

## Vulnerability / core concept

A textbook shortest-path problem: run Dijkstra over the transcribed weighted graph. The genuinely tricky part is the **flag-encoding rule**, which the worked example states ambiguously.

The example says the path "from A-PLANET to B-PLANET" is `PAPA, OSCAR, SIERRA, TANGO, 2025PLANET` and encodes to `POST2`. Notice the acronym contains neither `A` (A-PLANET) nor `B` (B-PLANET): it is built only from the **listed intermediate stops**, taking the first character of each (a digit counts, so `2025PLANET → 2`). The endpoints named in "from ... to ..." are *not* included in the acronym.

## Exploitation

Transcribe the map edges and run Dijkstra (`solve.py`):

```bash
python3 solve.py
```

The shortest route is:

```
Earth -> PALLUS-XA -> 12-PUCK-8 -> JIP-REIA -> TAYLOR-3489 -> LANCER-RXKRD
10.7 + 1.8 + 0.4 + 5.5 + 2.6 = 21.0
```

21.0 days, comfortably under the 25-day limit.

Now apply the encoding rule. Earth (origin) and LANCER-RXKRD (destination) are the "from/to" endpoints, so they are dropped — exactly as the example drops A-PLANET and B-PLANET. The acronym is the first character of each **intermediate** stop:

| Stop | PALLUS-XA | 12-PUCK-8 | JIP-REIA | TAYLOR-3489 |
|------|-----------|-----------|----------|-------------|
| First char | `P` | `1` | `J` | `T` |

Concatenate (`P1JT`) and append the total days to one decimal (`21.0`), separated by a dash:

```
CSSCTF{P1JT-21.0}
```

> Note: an initial submission that also included the initials of Earth (`E`) and Lancer (`L`) was rejected; re-reading the worked example shows the endpoints must be omitted.

## Flag

```
CSSCTF{P1JT-21.0}
```

## Key takeaways

- The map is just a weighted graph; Dijkstra over a hand-transcribed edge list solves it instantly.
- Read the flag-format example *literally* — here the "from/to" endpoints are excluded from the acronym, and a leading digit contributes as its own character.

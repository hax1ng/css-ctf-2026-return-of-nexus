# A Star Trail 2

**Category:** Misc · **Points:** 75 · **Solves:** 350 · **Challenge ID:** 24

> A 10,000-planet galactic map stored as linked Markdown files — chart the shortest flightpath from `S0jRxc` to `yRJyDb`.

## Challenge

> Congrats on your first, successful delivery cadet! Now that you've got a small taste of logistics and routing, take a gander at this larger galactic map. You've got quite a few more stops this time but thankfully, you won't have to be put to cryosleep now that you've gained your lightspeed vehicle licence. Today, your task is to make it from planetary body `S0jRxc` to planetary body `yRJyDb`. Chart out a path and **don't** be late; we expect you to make it there in a reasonable time. You'll have to do a bit of work to make sense of everything since our database is stored as Markdown files where each planet links to its neighbours with a wikilink but it should be easy work once you get used to it.
>
> Report to command your flightpath by taking the first letter of the ID of your first stop (`S0jRxc`), the second letter of your second stop, the third letter of your third stop, and so on, wrapping back around to the first letter on your 7th, 13th, 19th, etc. stop. Your flightpath flag is case sensitive. For example: if your path from ASTART to ZFINAL was BCDEFG, hijklm, NOPQRS, tuvwxy, ZFINAL the flag would be `CSSCTF{ACjQxL}`
>
> \- Polaris Logistics.

**Attachments:** `map.zip` (10,000 Markdown planet files; omitted here for size — see **Files**).

## Initial analysis

`map.zip` unpacks to exactly 10,000 `map/<ID>.md` files. Each file has a fixed shape:

```markdown
# S0jRxc

Coords: 1.937346, 1.274873

[[neighbourA]]
[[neighbourB]]
...
```

So every planet carries a 6-character ID, a 2-D coordinate, and a set of `[[wikilink]]` neighbours. A quick parse confirms all links resolve and are **reciprocal** (an undirected graph). The start `S0jRxc` sits at `(1.937346, 1.274873)`; the goal `yRJyDb` at `(99.893125, 99.361715)` — opposite corners of a 100×100 field.

## Vulnerability / core concept

This is a weighted shortest-path problem. The map has no explicit edge weights, but each planet's coordinates are given, so the natural travel time for a link is the **Euclidean distance between its endpoints**. Minimising total Euclidean distance (A\* with the straight-line heuristic, equivalently Dijkstra) yields the intended route — and, crucially, the route whose cyclic-index encoding spells readable text.

The flag encoding takes character `i % 6` from the ID of the `i`-th stop (0-based): char 0 of stop 1, char 1 of stop 2, …, wrapping every 6 stops.

## Exploitation

`solve.py` parses the ZIP directly, builds the reciprocal-link graph, weights each edge by endpoint distance, and runs A\* (cross-checked against plain Dijkstra):

```bash
python3 solve.py      # expects map.zip in the working directory
```

Key facts it reports:

- Minimum-distance route: **136 stops**, total cost `144.9333344480553` (straight-line lower bound `138.6230976894897`).
- A\* and independent Dijkstra return the **identical** route and cost.
- Every consecutive hop is a real reciprocal link.

A naive fewest-*hops* BFS gives only 14 stops but distance `199.95` and produces gibberish, confirming that **weighted** distance is the intended objective.

Applying the cyclic encoding to the 136-stop route:

```python
"CSSCTF{" + "".join(node[i % 6] for i, node in enumerate(route)) + "}"
```

produces a 136-character body made of recognizable geometry / graph-algorithm words (`STAR`, `map`, `Delaunay`, `Triangulation`, `Dijkstra`, `Voronoi`, `Graphs`, `determinant`, `colinear`, `algorithms`, `Lee and Schachter`, `tangents`, `merge`, `circumcircle`, `convex hull`, `geometry`) — strong confirmation the route and indexing are correct (and a direct hint toward the Delaunay rule used in A Star Trail 3).

## Flag

```
CSSCTF{STARmaPdElAUNaYTriaNGulATioNDIjKStrAVoRonoiGrAPHSdetERmiNaNTcolineaRALGOrITHmSLeEandsCHAcHTERTANgEnTSmErGECirCuMcIrcLEcOnVEXhuLLgeOMeTRy}
```

## Key takeaways

- When a graph gives coordinates but no weights, Euclidean distance between endpoints is the obvious — and here intended — edge cost.
- A readable decoded string is a free correctness oracle: the geometry vocabulary confirms both the route and the cyclic index.
- The flag's own words (`Delaunay`, `Voronoi`, `circumcircle`) foreshadow the edge-generation rule needed in part 3.

## Files

- `map.zip` — 2.6M — challenge input, **omitted for size**. Regenerate the solve by placing the official `map.zip` beside `solve.py`.

# A Star Trail 3

**Category:** Misc · **Points:** 120 · **Solves:** 206 · **Challenge ID:** 26

> The star-map database for Sector-A89J3 lost all its edges — infer the rule that generated them, rebuild the graph, and route `iJ2ZcO` → `pJk9vy`.

## Challenge

> Polaris Logistics has seemingly had a database corruption in the star maps of Sector-A89J3. With routing and deliveries unable to be completed for the foreseeable future, *you*, cadet, have been tasked with fixing this problem. Otherwise, you can consider yourself **fired**. Thankfully, all of the planetary body entries are still there, only their paths to neighbouring bodies have been destroyed. We can't seem to remember what rule we used to generate our routes but you can presumably find patterns in your previous postal appointments. Once you've got those records restored, get a move on with the next delivery from `iJ2ZcO` to `pJk9vy` to prove it.
>
> Report to command your flightpath by taking the first letter of the ID of your first stop (`iJ2ZcO`), the second letter of your second stop, the third letter of your third stop, and so on, wrapping back around to the first letter on your 7th, 13th, 19th, etc. stop. Your flightpath flag is case sensitive. (The flag for this challenge may not be easily recognisable)
>
> \- Polaris Logistics

**Attachments:** `map2.zip` (25,000 Markdown planet files with corrupted links; omitted here for size — see **Files**).

## Initial analysis

`map2.zip` holds 25,000 `map/<ID>.md` records. Each still has its ID and coordinates, but the neighbour list is gone — replaced by a `[CORRUPTED]` placeholder:

```markdown
# iJ2ZcO

Coords: 0.347730, 97.041287


[CORRUPTED]
```

Start `iJ2ZcO` is at `(0.347730, 97.041287)`; target `pJk9vy` at `(99.781280, 0.935324)`. We have every node's position but **no edges at all** — the graph must be regenerated from coordinates alone.

The prompt's clue is "patterns in your previous postal appointments": the directly related **A Star Trail 2** map (`map.zip`) still has all of its links intact, so it is the ground truth for whatever rule Polaris used.

## Vulnerability / core concept

Reverse-engineer the edge-generation rule from the intact previous map, then apply it here.

`infer_rule.py` reconstructs the undirected edge set of the Star Trail 2 map (29,972 edges from reciprocal wikilinks) and compares it against several coordinate-based graph constructions:

- **Delaunay triangulation** (`scipy.spatial.Delaunay`) → **29,972 / 29,972 edges match exactly — zero missing, zero extra.**
- Fixed-radius graphs and k-nearest-neighbour graphs (union and mutual, many `k`) → differ by thousands of edges.

So the rule is the **Delaunay triangulation** of the planet coordinates — consistent with the geometry vocabulary hidden in the part-2 flag (`Delaunay`, `Voronoi`, `circumcircle`, `Lee and Schachter`). `probe_graphs.py` double-checks that the alternative rules produce different routes/flags on *this* map, so the choice of rule actually matters.

## Exploitation

`solve.py` applies the confirmed rule end to end:

1. Parse all 25,000 records into IDs + coordinates.
2. Build the graph as the **Delaunay triangulation** of the coordinates (74,970 edges).
3. Weight each edge by Euclidean distance (same travel-time model as part 2).
4. Run A\*, cross-checked against Dijkstra, for `iJ2ZcO` → `pJk9vy`.

```bash
python3 solve.py map2.zip     # heavy graph build was run on kracken
```

Results:

- Minimum-distance route: **196 stops**, total cost `144.0473667550367` (straight-line lower bound `138.287334885592`).
- A\* and Dijkstra agree on route and cost; every hop is a genuine reconstructed Delaunay edge.

Encoding the 196-stop route with the same 0-based cyclic index (`node[i % 6]`) gives the flag. As the prompt warns, the body is **not** human-readable this time — it's just the correct character stream:

```python
"CSSCTF{" + "".join(identifiers[node][i % 6] for i, node in enumerate(route)) + "}"
```

## Flag

```
CSSCTF{itr6G8jMTXbOjCmClmMElZxQLqSXqnf53z1Z73liVas3ypn5CJZ4ZGlqZo6Fkc2onoJ6vx5SLfqqEyBotfjpxskQknpUgK9VMfBsFqzc0iEHDbMvv1hwXAo4U1NaimtTt9esb6mskMdUkbgBAjg3TTS1UeTSvf7LFZR0Vxf8KOgkzxHmvO0ifOFaVnwNgwUqpeo9}
```

## Key takeaways

- When edges are destroyed but a *related, intact* dataset exists, use it to fingerprint the generation rule rather than guessing.
- Delaunay triangulation reproduced the previous map's links perfectly (29,972/29,972); radius and k-NN models did not — an exact match is the strongest possible confirmation.
- With no readable-text oracle, correctness rests on the rule proof plus the A\*/Dijkstra cross-check.

## Files

- `map2.zip` — 5.5M — challenge input (25,000 corrupted records), **omitted for size**.
- `map.zip` (A Star Trail 2) — 2.6M — needed by `infer_rule.py` as the ground-truth graph, **omitted for size** (see the a-star-trail-2 writeup). Place both ZIPs beside the scripts to reproduce.

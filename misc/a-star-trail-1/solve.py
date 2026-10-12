#!/usr/bin/env python3
"""Shortest route transcribed from the official A_Star_Trail.png map."""

from collections import defaultdict
from heapq import heappop, heappush

edges = [
    ("Earth", "BACONITE", 5.0),
    ("Earth", "PALLUS-XA", 10.7),
    ("BACONITE", "C3810-ASQUAX-8", 2.1),
    ("BACONITE", "BARAT-BARAT", 9.8),
    ("C3810-ASQUAX-8", "BARAT-BARAT", 6.3),
    ("BARAT-BARAT", "JIP-REIA", 1.4),
    ("BARAT-BARAT", "PALLUS-XA", 1.4),
    ("PALLUS-XA", "12-PUCK-8", 1.8),
    ("PALLUS-XA", "HEMENS-RAJA-2", 2.5),
    ("JIP-REIA", "12-PUCK-8", 0.4),
    ("JIP-REIA", "TAYLOR-3489", 5.5),
    ("12-PUCK-8", "HEMENS-RAJA-2", 3.6),
    ("TAYLOR-3489", "TAMMY ASTEROID", 3.2),
    ("TAYLOR-3489", "LANCER-RXKRD", 2.6),
    ("HEMENS-RAJA-2", "TAMMY ASTEROID", 3.7),
    ("HEMENS-RAJA-2", "10-49-SLATER-4090", 6.0),
    ("TAMMY ASTEROID", "LANCER-RXKRD", 10.1),
    ("TAMMY ASTEROID", "VERGINON", 2.8),
    ("VERGINON", "LANCER-RXKRD", 8.5),
    ("VERGINON", "10-49-SLATER-4090", 7.5),
]

graph = defaultdict(list)
for a, b, days in edges:
    graph[a].append((b, days))
    graph[b].append((a, days))

queue = [(0, "Earth", ["Earth"])]
seen = set()
while queue:
    distance, node, route = heappop(queue)
    if node in seen:
        continue
    seen.add(node)
    if node == "LANCER-RXKRD":
        print(" -> ".join(route))
        print(" + ".join(str(next(w for v, w in graph[a] if v == b)) for a, b in zip(route, route[1:])), "=", round(distance, 1))
        # The example names different origin/destination planets than the
        # listed path, and only concatenates the listed intermediate stops.
        # The first submission including Earth and Lancer was rejected.
        print("intermediate initials:", "".join(name[0] for name in route[1:-1]))
        break
    for neighbor, weight in graph[node]:
        if neighbor not in seen:
            heappush(queue, (distance + weight, neighbor, route + [neighbor]))

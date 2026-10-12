#!/usr/bin/env python3
"""Restore the related map's Delaunay edges, then compute the minimum-distance flightpath."""
import heapq
import math
import re
import sys
import zipfile

import numpy as np
from scipy.spatial import Delaunay

START, TARGET = 'iJ2ZcO', 'pJk9vy'


def parse_map(path):
    identifiers, points = [], []
    pattern = re.compile(r'# ([A-Za-z0-9]{6})\n\nCoords: ([0-9.]+), ([0-9.]+)\n\n\n\[CORRUPTED\]\n')
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith('.md'):
                continue
            match = pattern.fullmatch(archive.read(name).decode())
            assert match and name == f'map/{match[1]}.md', name
            identifiers.append(match[1])
            points.append((float(match[2]), float(match[3])))
    assert len(identifiers) == 25000
    assert len(set(identifiers)) == len(identifiers)
    return identifiers, np.array(points, dtype=np.float64)


def make_graph(points):
    triangles = Delaunay(points).simplices
    neighbors = [set() for _ in points]
    for a, b, c in triangles:
        for u, v in ((a, b), (b, c), (c, a)):
            neighbors[u].add(v)
            neighbors[v].add(u)
    assert sum(map(len, neighbors)) % 2 == 0
    return [sorted(ns) for ns in neighbors]


def search(identifiers, points, neighbors, use_heuristic):
    by_name = {name: i for i, name in enumerate(identifiers)}
    source, target = by_name[START], by_name[TARGET]
    estimate = (lambda u: math.dist(points[u], points[target])) if use_heuristic else (lambda u: 0)
    queue = [(estimate(source), 0.0, source)]
    best = {source: 0.0}
    previous = {}
    settled = set()
    while queue:
        _, cost, u = heapq.heappop(queue)
        if u in settled or cost > best[u]:
            continue
        settled.add(u)
        if u == target:
            break
        for v in neighbors[u]:
            cost2 = cost + math.dist(points[u], points[v])
            if cost2 < best.get(v, math.inf):
                best[v] = cost2
                previous[v] = u
                heapq.heappush(queue, (cost2 + estimate(v), cost2, v))
    assert target in best
    route = [target]
    while route[-1] != source:
        route.append(previous[route[-1]])
    route.reverse()
    assert all(v in neighbors[u] for u, v in zip(route, route[1:]))
    assert math.isclose(best[target], sum(math.dist(points[u], points[v]) for u, v in zip(route, route[1:])), abs_tol=1e-9)
    return route, best[target], len(settled)


def main():
    identifiers, points = parse_map(sys.argv[1] if len(sys.argv) > 1 else 'map2.zip')
    neighbors = make_graph(points)
    route, cost, expanded = search(identifiers, points, neighbors, True)
    route2, cost2, expanded2 = search(identifiers, points, neighbors, False)
    assert route == route2 and math.isclose(cost, cost2, abs_tol=1e-9)
    body = ''.join(identifiers[node][i % 6] for i, node in enumerate(route))
    print('planets:', len(identifiers))
    print('edges:', sum(map(len, neighbors)) // 2)
    print('route stops:', len(route))
    print('route cost:', repr(cost))
    print('straight-line distance:', math.dist(points[route[0]], points[route[-1]]))
    print('A* expanded:', expanded, 'Dijkstra expanded:', expanded2)
    print('route:', ' -> '.join(identifiers[i] for i in route))
    print('flag:', 'CSSCTF{' + body + '}')

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Parse the official planetary map and find its minimum-distance flightpath."""

import heapq
import math
import re
import zipfile
from collections import deque

START = "S0jRxc"
GOAL = "yRJyDb"


def read_map(path="map.zip"):
    planets = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith(".md"):
                continue
            data = archive.read(name).decode("utf-8")
            identifier = re.search(r"^# (\w+)$", data, re.M).group(1)
            x, y = map(float, re.search(r"^Coords: ([\d.]+), ([\d.]+)$", data, re.M).groups())
            neighbors = re.findall(r"\[\[(\w+)\]\]", data)
            assert name == f"map/{identifier}.md"
            planets[identifier] = (x, y, neighbors)
    assert len(planets) == 10_000
    assert all(v in planets and u in planets[v][2]
               for u, (_, _, neighbors) in planets.items() for v in neighbors)
    return planets


def distance(planets, u, v):
    return math.dist(planets[u][:2], planets[v][:2])


def shortest_path(planets, heuristic=True):
    # A* with straight-line lower bound; heuristic=False is independent Dijkstra.
    estimate = lambda v: distance(planets, v, GOAL) if heuristic else 0.0
    queue = [(estimate(START), 0.0, START)]
    best = {START: 0.0}
    previous = {}
    visited = set()
    while queue:
        _, cost, u = heapq.heappop(queue)
        if u in visited:
            continue
        visited.add(u)
        if u == GOAL:
            break
        for v in planets[u][2]:
            new_cost = cost + distance(planets, u, v)
            if new_cost < best.get(v, float("inf")):
                best[v] = new_cost
                previous[v] = u
                heapq.heappush(queue, (new_cost + estimate(v), new_cost, v))
    assert GOAL in best
    route = [GOAL]
    while route[-1] != START:
        route.append(previous[route[-1]])
    return route[::-1], best[GOAL], len(visited)


def shortest_hops(planets):
    previous = {START: None}
    queue = deque([START])
    while queue:
        u = queue.popleft()
        if u == GOAL:
            break
        for v in planets[u][2]:
            if v not in previous:
                previous[v] = u
                queue.append(v)
    route = [GOAL]
    while route[-1] != START:
        route.append(previous[route[-1]])
    return route[::-1]


def flag(route):
    return "CSSCTF{" + "".join(node[i % 6] for i, node in enumerate(route)) + "}"


if __name__ == "__main__":
    planets = read_map()
    route, cost, expanded = shortest_path(planets)
    route2, cost2, expanded2 = shortest_path(planets, heuristic=False)
    hops = shortest_hops(planets)
    assert route == route2 and cost == cost2
    assert all(v in planets[u][2] for u, v in zip(route, route[1:]))
    print("A* expanded:", expanded)
    print("Dijkstra expanded:", expanded2)
    print("Euclidean lower bound:", distance(planets, START, GOAL))
    print("Shortest route stops:", len(route))
    print("Shortest route distance:", cost)
    print("Fewest-hop route stops:", len(hops))
    print("Fewest-hop route distance:", sum(distance(planets, u, v) for u, v in zip(hops, hops[1:])))
    print("Route:", " -> ".join(route))
    print("Flag:", flag(route))
    print("Fewest-hop alternative flag:", flag(hops))

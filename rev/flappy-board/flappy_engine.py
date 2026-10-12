#!/usr/bin/env python3
"""Faithful FLAPPY BOARD game engine + robust per-seed replay solver.

Transcribed directly from the stripped ELF `flappy_board`:
  sub_406c0f  (init)        sub_406cfe (step)
  sub_406bc6  (gap RNG)     sub_406b88 (xorshift32)

Replay semantics verified against the binary:
  * flap tick index  = game tick counter (arg1[3] / data_40b2ac) recorded
    BEFORE the step that consumes the flap.
  * round ends when score == target (state -> 7), stepping stops.
  * /api/complete body = round, wait_ms = wait_seconds*1000, ticks, score,
    flaps = comma-separated tick indices.

No network code lives here; see solve.py for the client.
"""
from __future__ import annotations


def xorshift32(x: int) -> int:
    x ^= (x << 13) & 0xffffffff
    x ^= x >> 17
    x ^= (x << 5) & 0xffffffff
    return x & 0xffffffff


class Game:
    __slots__ = ("y", "vel", "score", "ticks", "rng", "dead", "px", "pgap", "ppass")

    def __init__(self, seed: int):
        # sub_406c0f: y=0xf000, vel/score/ticks=0, rng = seed or 1
        self.y = 0xf000
        self.vel = 0
        self.score = 0
        self.ticks = 0
        self.rng = seed & 0xffffffff or 1
        self.dead = False
        # five pipes: x = (i*0x10e + 0x410) << 8 ; gap = sub_406bc6 ; passed = 0
        self.px = [0] * 5
        self.pgap = [0] * 5
        self.ppass = [False] * 5
        for i in range(5):
            self.px[i] = (i * 0x10e + 0x410) << 8
            self.pgap[i] = self._gap()
            self.ppass[i] = False

    def _gap(self) -> int:
        # sub_406bc6: advance rng then % 0xe7 + 0x7d
        self.rng = xorshift32(self.rng)
        return self.rng % 0xe7 + 0x7d

    def clone(self) -> "Game":
        g = Game.__new__(Game)
        g.y = self.y
        g.vel = self.vel
        g.score = self.score
        g.ticks = self.ticks
        g.rng = self.rng
        g.dead = self.dead
        g.px = self.px[:]
        g.pgap = self.pgap[:]
        g.ppass = self.ppass[:]
        return g

    def step(self, flap: bool) -> bool:
        """One physics tick (sub_406cfe). Returns True if still alive."""
        if self.dead or self.ticks > 0x8c9f:
            self.dead = True
            return False
        if flap:
            self.vel = -0x6bc
        self.vel += 0x43
        if self.vel > 0x800:
            self.vel = 0x800
        self.y += self.vel
        self.ticks += 1
        for i in range(5):
            self.px[i] -= 0x2cd
        if self.y <= 0xc00 or self.y > 0x1d3ff:
            self.dead = True
        for i in range(5):
            x = self.px[i]
            gap = self.pgap[i]
            if 0x7800 < x <= 0xd3ff:
                if (self.y - 0xbff <= (gap - 0x57) << 8) or (self.y + 0xbff >= (gap + 0x57) << 8):
                    self.dead = True
            if not self.ppass[i] and x <= 0x77ff:
                self.ppass[i] = True
                if not self.dead:
                    self.score += 1
        for i in range(5):
            if self.px[i] < -0x4400:          # signed 0xffffbc00
                newx = max(self.px) + 0x10e00
                self.px[i] = newx
                self.pgap[i] = self._gap()
                self.ppass[i] = False
        return not self.dead

    # index of the next pipe the bird must clear
    def next_pipe(self) -> int:
        best_i, best_x = -1, 1 << 62
        for i in range(5):
            if not self.ppass[i] and self.px[i] < best_x:
                best_i, best_x = i, self.px[i]
        if best_i < 0:                        # all passed (shouldn't happen mid-round)
            best_i = min(range(5), key=lambda i: self.px[i])
        return best_i


# ---------------------------------------------------------------------------
# Per-seed solvers.  We only ever need to solve 3 concrete seeds at run time,
# and we have unlimited offline attempts before the single online submission,
# so reliability beats speed.  Fast greedy sweep first, beam search fallback.
# ---------------------------------------------------------------------------

DEAD_LOW = 0xc00
DEAD_HIGH = 0x1d3ff
BIRD_HALF = 0xbff
GAP_HALF = 0x57 << 8


def _greedy(seed: int, target: int, threshold: float, lookahead: float):
    g = Game(seed)
    flaps = []
    while g.score < target and not g.dead:
        i = g.next_pipe()
        center = g.pgap[i]                    # pixel units
        y = g.y / 256.0
        vel = g.vel / 256.0
        flap = (y + max(0.0, vel) * lookahead >= center + threshold) and vel >= 0
        if flap:
            flaps.append(g.ticks)
        g.step(flap)
    return g, flaps


def solve_greedy(seed: int, target: int):
    combos = [(48, 0), (35, 0), (40, 0), (45, 0), (50, 0), (55, 0), (30, 0),
              (60, 0), (25, 0), (65, 0), (20, 0), (40, 2), (45, 2), (50, 2),
              (35, 2), (55, 2), (40, 4), (50, 4), (30, 4), (60, 4),
              (45, 1), (50, 1), (40, 1), (55, 3), (35, 3)]
    best = None
    for t, l in combos:
        g, flaps = _greedy(seed, target, t, l)
        if g.score >= target and not g.dead:
            return g, flaps
        if best is None or g.score > best[0].score:
            best = (g, flaps)
    return best


def _corridor_penalty(g: Game) -> float:
    """How far the bird is from safely clearing the imminent pipe(s)."""
    pen = 0.0
    for i in range(5):
        x = g.px[i]
        if x <= 0x77ff or x > 0x14000:        # already passed or far away
            continue
        gap = g.pgap[i]
        lo = ((gap - 0x57) << 8) + BIRD_HALF
        hi = ((gap + 0x57) << 8) - BIRD_HALF
        # weight rises sharply as the pipe nears the collision zone
        nearness = max(0.0, 1.0 - (x - 0x7800) / float(0x14000 - 0x7800))
        if g.y < lo:
            pen += (lo - g.y) * (1.0 + 4.0 * nearness)
        elif g.y > hi:
            pen += (g.y - hi) * (1.0 + 4.0 * nearness)
    # gentle pull toward vertical middle keeps options open
    pen += abs(g.y - 0xf000) * 0.02
    return pen


def solve_beam(seed: int, target: int, width: int = 400, max_ticks: int = 40000):
    """Beam search over flap/no-flap. Returns (game, flaps) reaching target."""
    start = Game(seed)
    # beam entries: (game, flaps_tuple)
    beam = [(start, ())]
    for _ in range(max_ticks):
        # success check
        for g, fl in beam:
            if g.score >= target and not g.dead:
                return g, list(fl)
        cand = []
        for g, fl in beam:
            if g.dead:
                continue
            for flap in (False, True):
                ng = g.clone()
                tick_here = ng.ticks
                ng.step(flap)
                if ng.dead:
                    continue
                nfl = fl + (tick_here,) if flap else fl
                cand.append((ng, nfl))
        if not cand:
            break
        # rank: more score, then lower corridor penalty
        cand.sort(key=lambda gf: (-gf[0].score, _corridor_penalty(gf[0])))
        # de-dup on coarse (y,vel,score,tick) to keep the beam diverse
        seen = set()
        beam = []
        for g, fl in cand:
            key = (g.score, g.ticks, g.y >> 9, g.vel >> 7)
            if key in seen:
                continue
            seen.add(key)
            beam.append((g, fl))
            if len(beam) >= width:
                break
    # best effort
    beam.sort(key=lambda gf: (-gf[0].score, _corridor_penalty(gf[0])))
    return beam[0] if beam else (start, [])


def solve_seed(seed: int, target: int, verbose: bool = False):
    """Return (ticks, score, flaps) for a valid replay, or raise if impossible."""
    g, flaps = solve_greedy(seed, target)
    if g.score >= target and not g.dead:
        if verbose:
            print(f"[greedy] seed={seed} target={target} -> ticks={g.ticks} flaps={len(flaps)}")
        return g.ticks, target, flaps
    for w in (400, 800, 1600, 3000):
        g, flaps = solve_beam(seed, target, width=w)
        if g.score >= target and not g.dead:
            if verbose:
                print(f"[beam w={w}] seed={seed} target={target} -> ticks={g.ticks} flaps={len(flaps)}")
            return g.ticks, target, flaps
    raise RuntimeError(f"could not solve seed={seed} target={target} (best score {g.score})")


def verify_replay(seed: int, target: int, flaps, ticks):
    """Re-simulate the exact flap list (as the server will) and confirm it
    reaches `target` alive at `ticks`. Mirrors server-side re-simulation."""
    g = Game(seed)
    fset = set(flaps)
    while not g.dead:
        if g.score >= target:
            break
        g.step(g.ticks in fset)
    ok = (g.score >= target and not g.dead and g.ticks == ticks)
    return ok, g.score, g.ticks, g.dead


if __name__ == "__main__":
    import sys
    seed = int(sys.argv[1], 0) if len(sys.argv) > 1 else 123456789
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    ticks, score, flaps = solve_seed(seed, target, verbose=True)
    ok, s, t, dead = verify_replay(seed, target, flaps, ticks)
    print(f"seed={seed} target={target} ticks={ticks} score={score} flaps={len(flaps)}")
    print(f"verify: ok={ok} score={s} ticks={t} dead={dead}")
    print("flaps=" + ",".join(map(str, flaps)))

#!/usr/bin/env python3
"""Offline FLAPPY BOARD replay simulator and candidate scheduler.

No network use.  The state transitions are transcribed from sub_406c0f,
sub_406cfe, sub_406b88, and sub_406bc6 in the supplied ELF.
"""
import argparse
import random


def xorshift32(x):
    x ^= (x << 13) & 0xffffffff
    x ^= x >> 17
    x ^= (x << 5) & 0xffffffff
    return x & 0xffffffff


class Game:
    def __init__(self, seed):
        self.y = 0xf000
        self.vel = 0
        self.score = 0
        self.ticks = 0
        self.rng = seed or 1
        self.dead = False
        self.pipes = []
        for i in range(5):
            self.rng = xorshift32(self.rng)
            gap = self.rng % 0xe7 + 0x7d
            self.pipes.append([(i * 0x10e + 0x410) << 8, gap, False])

    def step(self, flap=False):
        if self.dead or self.ticks > 0x8c9f:
            self.dead = True
            return False
        if flap:
            self.vel = -0x6bc
        self.vel = min(self.vel + 0x43, 0x800)
        self.y += self.vel
        self.ticks += 1
        for pipe in self.pipes:
            pipe[0] -= 0x2cd
        if self.y <= 0xc00 or self.y > 0x1d3ff:
            self.dead = True
        for pipe in self.pipes:
            x, gap, passed = pipe
            if 0x7800 < x <= 0xd3ff:
                if self.y - 0xbff <= (gap - 0x57) << 8 or self.y + 0xbff >= (gap + 0x57) << 8:
                    self.dead = True
            if not passed and x <= 0x77ff:
                pipe[2] = True
                if not self.dead:
                    self.score += 1
        for pipe in self.pipes:
            if pipe[0] < -0x4400:
                self.rng = xorshift32(self.rng)
                pipe[:] = [max(p[0] for p in self.pipes) + 0x10e00, self.rng % 0xe7 + 0x7d, False]
        return not self.dead

    def next_pipe(self):
        return min((p for p in self.pipes if not p[2]), key=lambda p: p[0])


def solve(seed, target=30, threshold=48, lookahead=0):
    g = Game(seed)
    flaps = []
    while g.score < target and not g.dead:
        pipe = g.next_pipe()
        # A single flap reverses downward velocity and causes ~80px of climb.
        # The next pipe's safe corridor is center +/- ~75px.
        center = pipe[1]
        y = g.y / 256
        velocity = g.vel / 256
        flap = y + max(0, velocity) * lookahead >= center + threshold and velocity >= 0
        if flap:
            flaps.append(g.ticks)
        g.step(flap)
    return g, flaps


def solve_adaptive(seed, target=30, threshold=48, lookahead=0):
    first = solve(seed, target, threshold, lookahead)
    if first[0].score == target and not first[0].dead:
        return first
    best = first
    for t, l in [(35, 0), (40, 0), (45, 0), (50, 0), (55, 0),
                 (30, 0), (60, 0), (40, 2), (45, 2), (50, 2),
                 (40, 4), (50, 4)]:
        result = solve(seed, target, t, l)
        if result[0].score == target and not result[0].dead:
            return result
        if result[0].score > best[0].score:
            best = result
    return best


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--seed', type=lambda s: int(s, 0))
    p.add_argument('--target', type=int, default=30)
    p.add_argument('--threshold', type=float, default=48)
    p.add_argument('--lookahead', type=int, default=0)
    p.add_argument('--test', type=int, default=0)
    p.add_argument('--round', type=int, choices=(1, 2, 3))
    p.add_argument('--wait-seconds', type=int)
    p.add_argument('--form', action='store_true', help='print the offline /api/complete POST body only')
    a = p.parse_args()
    if a.test:
        rng = random.Random(27)
        failures = []
        for i in range(a.test):
            seed = rng.randrange(1, 1 << 32)
            game, _ = solve_adaptive(seed, a.target, a.threshold, a.lookahead)
            if game.score != a.target:
                failures.append((seed, game.score, game.ticks))
        print({'tested': a.test, 'success': a.test-len(failures), 'failures': failures[:20]})
    else:
        if a.seed is None:
            p.error('--seed required unless --test supplied')
        if a.round is not None:
            expected = a.round * 10
            if a.target != 30 and a.target != expected:
                p.error('--target disagrees with --round')
            a.target = expected
        game, flaps = solve_adaptive(a.seed, a.target, a.threshold, a.lookahead)
        if a.form:
            if a.round is None or a.wait_seconds is None:
                p.error('--form requires --round and --wait-seconds from the same authorized session')
            if game.score != a.target or game.dead:
                p.error('offline replay failed to reach target')
            print(f'round={a.round}&wait_ms={a.wait_seconds * 1000}'
                  f'&ticks={game.ticks}&score={game.score}'
                  f'&flaps={",".join(map(str, flaps))}')
        else:
            print({'score': game.score, 'ticks': game.ticks, 'dead': game.dead, 'flaps': flaps})


if __name__ == '__main__':
    main()

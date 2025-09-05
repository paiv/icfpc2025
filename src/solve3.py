#!/usr/bin/env python
import itertools
import logging
import random
from fractions import Fraction as frac
from pathlib import Path


_logger = logging.getLogger(Path(__file__).name)


class _State:
    def __init__(self, size):
        self.size = size
        self.doors = [-1] * (size * 6)
        self.probs = [frac(0)] * (size * 6 * 6)
        self.visits = [0] * (size * 6 * 6)

    def update(self, plan, result):
        for ps, res in zip(plan, result):
            pos = res[0]
            for i, to in zip(ps, res[1:]):
                ix = pos * 6 + i
                jx = ix * 6
                self.doors[ix] = to
                kn = [j for j in range(6) if self.doors[to * 6 + j] == pos]
                if kn:
                    for j in kn:
                        self.visits[jx + j] += 1
                        self.probs[jx + j] += frac(1, len(kn))
                        ux = to * 6 + j
                        self.visits[ux * 6 + i] += 1
                        self.probs[ux * 6 + i] += frac(1, len(kn))
                else:
                    for j in range(6):
                        self.visits[jx + j] += 1
                        self.probs[jx + j] += frac(1, 6)
                pos = to

    def connections(self):
        probs = [p/n if n else 0 for p,n in zip(self.probs, self.visits)]
        seen = set()
        res = list()
        for a in range(self.size):
            for i in range(6):
                ix = a * 6 + i
                b = self.doors[ix]
                if b < 0: return
                js = probs[ix*6: ix*6+6]
                _,j = sorted([(-p,j) for j,p in enumerate(js)])[0]
                p = tuple(sorted([(a,i), (b,j)]))
                if p in seen: continue
                seen.add(p)
                res.append(p)
        return res


def solve(api, size):
    state = _State(size)
    while True:
        plan = [[random.randrange(6) for _ in range(18 * size)] for _ in range(1)]
        splan = [''.join(map(str, ps)) for ps in plan]
        result = api.explore(splan)
        state.update(plan, result)
        cons = state.connections()
        if cons: break
    _logger.info('connections %s', cons)
    rooms = list(range(size))
    return (rooms, 0, cons)

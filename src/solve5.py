#!/usr/bin/env python
import itertools
import logging
import random
from collections import defaultdict, deque
from pathlib import Path


_logger = logging.getLogger(Path(__file__).name)


class _Rooms:
    def __init__(self):
        self.rooms = dict()

    def __getitem__(self, key):
        ps = self.rooms.get(key)
        if ps is None:
            ps = [None] * 6
            self.rooms[key] = ps
        return ps

    def items(self):
        return self.rooms.items()


class _State:
    def __init__(self, size):
        self.size = size
        self.start = None
        self.data = dict()
        self.sigs = dict()
        self.rooms = _Rooms()
        self.doors = defaultdict(set)

    def update(self, plans, results):
        for plan, result in zip(plans, results):
            self.data[b''] = result[0]
            self.data[bytes(plan)] = result[-1]
            self.rooms[bytes(plan[:-1])][plan[-1]] = result[-1]
        for plan, result in zip(plans, results):
            r0 = bytes(plan[:-1])
            s0 = tuple(self.rooms[r0][i] for i in range(6))
            if None in s0: continue
            self.sigs[r0] = s0
            if len(plan) > 2:
                r1 = bytes(plan[:-2])
                r2 = bytes(plan[:-3])
                s1 = self.sigs.get(r1)
                s2 = self.sigs.get(r2)
                if (s1 is not None) and (s2 is not None):
                    if s2 == s0:
                        self.doors[r0].add(r1)
                        self.doors[r1].add(r0)

    def fromsig(self, sig):
        g = (k for k,q in self.sigs.items() if q == sig)
        return next(g, None)

    def equiv(self, a):
        if (s := self.sigs.get(a)) is None:
            return
        return self.fromsig(s)

    def connections(self):
        names = dict()
        cons = list()
        fringe = deque([b''])
        seen = set()
        while fringe:
            a = fringe.popleft()
            n = self.equiv(a)
            if (n is None) or (n in seen): continue
            seen.add(n)
            names[n] = len(names)
            for i in range(6):
                k = a + bytes([i])
                to = self.doors.get(k)
                if to is None: return
                for t in to:
                    cons.append((k, t))
                    fringe.append(k)
        res = list()
        for a, b in cons:
            p = [(names[self.equiv(a[:-1])], a[-1]), (names[self.equiv(b[:-1])], b[-1])]
            p = tuple(sorted(p))
            if p in res: continue
            res.append(p)
        start = names[b'']
        names = [self.data[k] for k,_ in names.items()]
        return (names, start, res)


class _Planner:
    def plan(self, state):
        plans = list()
        fringe = deque([b''])
        while fringe:
            a = fringe.popleft()
            v = state.rooms[a]
            if None in v:
                plan = [list(a) + [i] for i in range(6)]
                plans.extend(plan)
            else:
                for i in range(6):
                    fringe.append(a + bytes([i]))
        return plans


def solve(api, size):
    state = _State(size)
    planner = _Planner()
    for t in itertools.count():
        plan = planner.plan(state)
        splan = [''.join(map(str, ps)) for ps in plan]
        result = api.explore(splan)
        state.update(plan, result)
        cons = state.connections()
        if cons: break
    _logger.info('connections %s', cons)
    return cons

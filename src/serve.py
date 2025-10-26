#!/usr/bin/env python
import html
import http.server
import json
import logging
import random
import re
import string
import subprocess
import sys
import tempfile
import urllib.parse
from collections import deque
from pathlib import Path


_Router = dict()
_Env = dict()
_logger = logging.getLogger(Path(__file__).name)


def route(path, method='GET'):
    def inner(handler):
        rx = re.compile(f'^{path}$')
        _Router[(method,path)] = (rx, handler)
    return inner


def send_response(request, body, code=200, content_type='text/plain'):
    body = body.encode()
    request.send_response(code)
    request.send_header('Content-Type', content_type)
    request.send_header('Content-Length', len(body))
    request.end_headers()
    request.wfile.write(body)


def send_json(request, body, code=200):
    return send_response(request, json.dumps(body), code, 'application/json')


def send_error(request, body, code=400):
    return send_json(request, body, code=code)


@route(r'/select', method='POST')
def process_select(request, query, post):
    name = post.get('problemName')
    seed = post.get('seed')
    prob = genproblem(name, seed=seed)
    _Env['problem'] = None
    _Env['total'] = 0
    if not prob:
        return send_error(request, dict(error=f'invalid problem {json.dumps(name)}'))
    _Env['problem'] = prob
    if (fn := _Env.get('savefile')):
        fn = Path(fn).with_suffix('.json')
        fn.write_text(json.dumps(prob))
        _dumpimage(prob, fn.with_suffix('.svg'))
    send_json(request, dict(problemName=name))


@route(r'/explore', method='POST')
def process_explore(request, query, post):
    prob = _Env.get('problem')
    if not prob:
        return send_error(request, dict(error='no problem selected'))
    total = _Env.get('total', 0)
    plans = post.get('plans')
    try:
        res = explore_problem(prob, plans)
        total += len(plans) + 1
    except ValueError as err:
        return send_error(request, dict(error=str(err)))
    _Env['problem'] = prob
    _Env['total'] = total 
    send_json(request, dict(results=res, queryCount=total))


@route(r'/guess', method='POST')
def process_guess(request, query, post):
    prob = _Env.get('problem')
    if not prob:
        return send_error(request, dict(error='no problem selected'))
    guess = post.get('map')
    try:
        res = validate_guess(prob, guess)
    except ValueError as err:
        return send_error(request, dict(error=str(err)))
    _Env['problem'] = None
    _Env['total'] = 0
    send_json(request, dict(correct=res))


class RequestHandler (http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        rpath,*query = self.path.split('?', maxsplit=1)
        query = urllib.parse.parse_qs(query[0]) if query else dict()
        for (method,path), (rx, handler) in _Router.items():
            if method != 'GET': continue
            if (m := rx.search(rpath)):
                return handler(self, *m.groups(), query)
        else:
            self.send_error(404, explain=f'No route for {self.path!r}')

    def do_POST(self):
        rpath,*query = self.path.split('?', maxsplit=1)
        query = urllib.parse.parse_qs(query[0]) if query else None
        for (method,path), (rx, handler) in _Router.items():
            if method != 'POST': continue
            if (m := rx.search(rpath)):
                h = self.headers.get('content-type')
                if h is not None:
                    h,*_ = h.split(';')
                if h not in ('application/x-www-form-urlencoded', 'application/json'):
                    return self.send_error(400, explain=f'No handler for {h}')
                n = int(self.headers.get('content-length', -1))
                body = b''
                while n > 0:
                    chunk = self.rfile.read(n)
                    n -= len(chunk)
                    body += chunk
                if h == 'application/x-www-form-urlencoded':
                    params = urllib.parse.parse_qs(body.decode())
                elif h == 'application/json':
                    params = json.loads(body)
                return handler(self, *m.groups(), query, params)
        else:
            self.send_error(404, explain=f'No route for {self.path!r}')


def _genlighting(size, seed=None):
    rng = random.Random(seed)
    rooms = list(range(size))
    doors = [(a, i) for a in rooms for i in range(6)]
    names = list(range(4))
    trunk = list(range(size))
    rng.shuffle(rooms)
    rng.shuffle(doors)
    rng.shuffle(names)
    rng.shuffle(trunk)
    names = (names * ((size + 3) // 4))[:size]
    rng.shuffle(names)
    doors = set(doors)
    cons = list()
    for (j, s) in enumerate(trunk[1:], 1):
        t = rng.choice(trunk[:j])
        while True:
            a = rng.choice([(t, i) for i in range(6)])
            if a in doors:
                doors.remove(a)
                break
        while True:
            b = rng.choice([(s, i) for i in range(6)])
            if b in doors:
                doors.remove(b)
                break
        cons.append((a, b))
    while doors:
        a = doors.pop()
        if not doors or rng.random() < 0.1:
            b = a
        else:
            b = doors.pop()
        cons.append((a, b))
    cons = [((rooms.index(a), i), (rooms.index(b), j)) for (a,i),(b,j) in cons]
    cons = [{'from':dict(room=a, door=i), 'to':dict(room=b, door=j)}
        for (a,i),(b,j) in cons]
    start = rng.randrange(size)
    return dict(rooms=names, startingRoom=start, connections=cons)


def genproblem(name, /, seed=None):
    if not name: return
    problems = _Env['problems']
    params = problems.get(name)
    if not params: return
    size, kind = params
    if kind == 'l':
        return _genlighting(size, seed)


def parsegrid(prob):
    grid = dict()
    cons = prob['connections']
    for obj in cons:
        a = obj['from']['room']
        i = obj['from']['door']
        b = obj['to']['room']
        j = obj['to']['door']
        grid[(a,i)] = (b,j)
        if (t := grid.get((b,j))):
            if t != (a,i):
                print(f'invalid room connection {(a,i)} - {(b,j)} - {t}', file=sys.stderr)
        grid[(b,j)] = (a,i)
    return grid


def explore_problem(prob, plans):
    grid = parsegrid(prob)
    def walk(plan):
        rooms = prob['rooms']
        ps = list()
        pos = prob['startingRoom']
        ps.append(rooms[pos])
        for i in plan:
            to = grid.get((pos, i))
            if to is None: raise ValueError(f'invalid door {i}')
            pos, _ = to
            ps.append(rooms[pos])
        return ps
    res = [walk(list(map(int, s))) for s in plans]
    return res


def validate_guess(prob, guess):
    room1 = prob['rooms']
    room2 = guess['rooms']
    start1 = prob['startingRoom']
    start2 = guess['startingRoom']
    if room1[start1] != room2[start2]:
        return False
    cons1 = parsegrid(prob)
    cons2 = parsegrid(guess)
    doors = {(a,i) for a in range(len(room1)) for i in range(6)}
    fringe = deque([(start1, start2)])
    seen = set()
    while fringe:
        a1, a2 = fringe.popleft()
        if a1 in seen: continue
        seen.add(a1)
        for i in range(6):
            b1, j1 = cons1[(a1, i)]
            t = cons2.get((a2, i))
            if t is None:
                raise ValueError(f'Room {a2} door {i} not connected to anything')
            b2, j2 = t
            if room1[b1] != room2[b2]:
                return False
            doors.discard((a2, i))
            fringe.append((b1, b2))
    if doors:
        a,i = doors.pop()
        raise ValueError(f'Room {a} door {i} not connected to anything')
    return True


def _dumpimage(prob, filename):
    t = Path(filename).suffix[1:].lower()
    viz = str(Path(__file__).parent / 'viz.py')
    with tempfile.NamedTemporaryFile(mode='w', delete_on_close=False) as file:
        json.dump(prob, file)
        file.close()
        p = subprocess.run(['python', viz, file.name], stdout=subprocess.PIPE)
        p.check_returncode()
        s = p.stdout
    p = subprocess.run(['dot', f'-T{t}', '-o' + str(filename)], input=s)
    p.check_returncode()


def setup(savefile):
    problems = {
        'probatio': (3, 'l'),
        'primus': (6, 'l'),
        'secundus': (12, 'l'),
        'tertius': (18, 'l'),
        'quartus': (24, 'l'),
        'quintus': (30, 'l'),
    }
    _Env['problems'] = problems
    _Env['savefile'] = savefile


def main(args):
    setup(args.save)
    address, port = args.address, args.port
    server = http.server.ThreadingHTTPServer((address, port), RequestHandler)
    _logger.info(f'Serving HTTP on {address} port {port} (http://{address}:{port}/) ...')
    server.serve_forever()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--address', default='127.0.0.1', help='bind address')
    parser.add_argument('port', nargs='?', type=int, default=8000, help='bind port')
    parser.add_argument('-s', '--save', help='save problem file and image')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    args = parser.parse_args()
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=level)
    main(args)

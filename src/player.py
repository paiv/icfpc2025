#!/usr/bin/env python
import http
import json
import logging
import requests
import time
import tomllib
from pathlib import Path
from urllib.parse import urljoin


_DefaultUrl = 'https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com/'
_logger = logging.getLogger(Path(__file__).name)


def fproc(filt, prog, *args, **kwargs):
    with tempfile.NamedTemporaryFile(delete_on_close=False) as temp:
        filt(temp, *args)
        temp.close()
        name = str(Path(__file__).parent / prog)
        _logger.debug(f"run '{name}' '{temp.name}'")
        p = subprocess.run([name, temp.name],
            capture_output=True, text=True,
            **kwargs)
        if p.stderr:
            _logger.error('%s', p.stderr)
        p.check_returncode()
        return p


class ApiClient:
    def __init__(self, baseurl, timeout=30):
        self.ses = requests.Session()
        self.baseurl = baseurl
        self.timeout = timeout
        self._config()

    def _config(self):
        if Path('.env').is_file():
            with open('.env', 'rb') as fp:
                config = tomllib.load(fp)
                headers = config['wget']['headers']
                for k,v in headers.items():
                    self.ses.headers[k] = v

    def _auth(self, obj):
        if Path('.env').is_file():
            with open('.env', 'rb') as fp:
                config = tomllib.load(fp)
                auth = config['icfpc']['id']
                obj['id'] = auth
        return obj

    def _request(self, *args, **kwargs):
        rlimit = int(http.HTTPStatus.TOO_MANY_REQUESTS)
        delay = 1
        for _ in range(10):
            r = self.ses.request(*args, timeout=self.timeout, **kwargs)
            if r.ok: return r
            if r.status_code != rlimit and r.status_code < 500:
                break
            _logger.warning(f'{r.status_code} on {method} {url}')
            time.sleep(delay)
            delay *= 2.07
        if not r.ok:
            _logger.error(r.content)
        r.raise_for_status()


    def _api(self, url, json, *args, **kwargs):
        url = urljoin(self.baseurl, url)
        json = self._auth(json)
        r = self._request('POST', url, *args, json=json, **kwargs)
        media = r.headers['content-type']
        _logger.debug(media)
        obj = r.json()
        _logger.debug(obj)
        return obj


    def _post(self, url, **kwargs):
        return self._api(url, self._auth(kwargs))

    def select(self, pid):
        self._post('/select', problemName=pid)

    def explore(self, plans):
        res = self._post('/explore', plans=plans)
        return res['results']

    def guess(self, rooms, start, connections):
        cons = [{"from":dict(room=a, door=i), "to":dict(room=b, door=j)}
            for (a,i),(b,j) in connections]
        obj = dict(
            rooms=rooms,
            startingRoom=start,
            connections=cons
        )
        _logger.debug('guess %s', obj)
        res = self._post('/guess', map=obj)
        _logger.info('%s', res)
        return res


def handle_select(args):
    api = ApiClient(args.url)
    api.select(args.pid)


def handle_solve(args):
    if not args.solver:
        parser.error('argument -s/--solver: requires a value')
    solver = __import__(args.solver)
    size = args.size
    api = ApiClient(args.url)
    rooms, start, cons = solver.solve(api, size)
    res = api.guess(rooms=rooms, start=start, connections=cons)
    print(res)


def handle_snipe(args):
    if not args.solver:
        parser.error('argument -s/--solver: requires a value')
    solver = __import__(args.solver)
    size = args.size
    api = ApiClient(args.url)
    api.select(args.pid)
    rooms, start, cons = solver.solve(api, size)
    res = api.guess(rooms=rooms, start=start, connections=cons)
    print(res)


def handle_cheese(args):
    import random
    if not args.solver:
        parser.error('argument -s/--solver: requires a value')
    solver = __import__(args.solver)
    if not args.cheeser:
        parser.error('argument -c/--cheeser: requires a value')
    cheeser = __import__(args.cheeser)
    api = ApiClient(args.url)
    res = cheeser.cheese(solver, api, args.pid, args.size)
    print(res)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    subps = parser.add_subparsers(required=True)
    parser.add_argument('-v', '--verbose', action='count', default=0,
        help='verbose output (-vvv)')
    parser.add_argument('-u', '--url', default=_DefaultUrl,
        help='base URL (default %(default)s)')
    parser.add_argument('-s', '--solver', help='solver module')
    parser.add_argument('-c', '--cheeser', help='cheesing module')

    pselect = subps.add_parser('select')
    pselect.set_defaults(handler=handle_select)
    pselect.add_argument('pid', help='problem id')

    psolve = subps.add_parser('solve')
    psolve.set_defaults(handler=handle_solve)
    psolve.add_argument('size', type=int, help='problem size')

    psnipe = subps.add_parser('snipe')
    psnipe.set_defaults(handler=handle_snipe)
    psnipe.add_argument('pid', help='problem id')
    psnipe.add_argument('size', type=int, help='problem size')

    pcheese = subps.add_parser('cheese')
    pcheese.set_defaults(handler=handle_cheese)
    pcheese.add_argument('pid', help='problem id')
    pcheese.add_argument('size', type=int, help='problem size')

    args = parser.parse_args()
    level = [logging.WARNING, logging.INFO, logging.DEBUG][min(args.verbose, 2)]
    logging.basicConfig(level=level)
    if level <= logging.DEBUG:
        from http.client import HTTPConnection
        HTTPConnection.debuglevel = 1

    args.handler(args)

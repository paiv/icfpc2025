#!/usr/bin/env python
import json
import re
import string
import textwrap


def parsecons(text):
    cons = None
    rooms = None
    try:
        cons = json.loads(text)
    except json.JSONDecodeError:
        pass
    if cons is None:
        xs = list(map(int, re.findall(r'\d+', text)))
        cons = [((a,i),(b,j)) for p in range(0, len(xs), 4)
            for a,i,b,j in [xs[p:p+4]]]
    elif isinstance(cons, dict):
        cons = cons.get('map', cons)
        rooms = cons.get('rooms')
        cons = cons['connections']
    if cons and isinstance(cons[0], dict):
        cons = [((o['from']['room'], o['from']['door']),
            (o['to']['room'], o['to']['door'])) for o in cons]
    return (rooms, cons)


def main(args):
    text = args.input.read()
    labels, cons = parsecons(text)
    rooms = {x for (a,i),(b,j) in cons for x in [a,b]}
    tdoc = '''\
graph {
  bgcolor = "#202124";
  node [
    shape = "record"
    color = "#5F626B"
    fontcolor = "#f1f3f4"
  ];
$rooms
$edges
}\
'''
    troom = 'room$a [label = "<f0> Room $a$k|<f1> 0|<f2> 1|<f3> 2|<f4> 3|<f5> 4|<f6> 5"];'
    tedge = 'room$a:f$i -- room$b:f$j [color = "$c 0.80 0.95 0.75"];'
    rooms = [string.Template(troom).substitute(a=a, k=k)
        for a in rooms
        for k in [f' ({labels[a]})' if labels else '']]
    edges = list()
    for (a,i),(b,j) in cons:
        c = round(((i+1) * (j+1)) % 8 / 8, 3)
        edges.append(string.Template(tedge)
            .substitute(a=a, i=i+1, b=b, j=j+1, c=c))
    s = string.Template(tdoc).substitute(
        rooms=textwrap.indent('\n'.join(rooms), '  '),
        edges=textwrap.indent('\n'.join(edges), '  '))
    print(s)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=argparse.FileType())
    args = parser.parse_args()
    main(args)

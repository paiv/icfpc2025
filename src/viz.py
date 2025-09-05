#!/usr/bin/env python
import re
import string
import textwrap


def main(args):
    text = args.input.read()
    xs = list(map(int, re.findall(r'\d+', text)))
    ps = xs[0::4]
    pi = xs[1::4]
    qt = xs[2::4]
    qj = xs[3::4]
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
    troom = 'room$a [label = "<f0> Room $a|<f1> 0|<f2> 1|<f3> 2|<f4> 3|<f5> 4|<f6> 5"];'
    tedge = 'room$a:f$i -- room$b:f$j [color = "$c 0.80 0.95 0.75"];'
    rooms = [string.Template(troom).substitute(a=a)
        for a in set(ps + qt)]
    edges = list()
    for a,i,b,j in zip(ps, pi, qt, qj):
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

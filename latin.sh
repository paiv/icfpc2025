#!/bin/sh

SOLVER="${SOLVER:-solve6}"
echo $SOLVER

probs=(
    "probatio 3"
    "primus 6"
    "secundus 12"
    "tertius 18"
    "quartus 24"
    "quintus 30"
    )

for i in "${probs[@]}"; do
    echo $i
    src/player.py -s $SOLVER snipe $i
done

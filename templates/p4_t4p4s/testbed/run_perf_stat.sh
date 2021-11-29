#!/bin/bash

RUNS=$1
EVENTS=$2
DURATION=$3

for i in $(seq 1 $RUNS) ;
do
        echo Run $i ;
        perf stat -C {{ cores }} -x, -e ${EVENTS} sleep ${DURATION} ;
done

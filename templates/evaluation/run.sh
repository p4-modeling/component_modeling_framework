#!/bin/bash

source venv/bin/activate
python3 plot_perf_stat.py "$@" 2>&1 | tee -a evaluation.log
python3 plot_throughput.py "$@" 2>&1 | tee -a evaluation.log
make

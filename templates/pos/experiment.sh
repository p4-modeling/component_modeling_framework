#!/bin/bash

set -xe

# determine experiment root folder
ROOT=$(dirname $(realpath $0))/..
EXP=${ROOT}/experiment
EVALUATION=${ROOT}/evaluation

if test "$#" -ne 2; then
	echo "Usage: setup.sh loadgen-experiment-node dut-experiment-node"
	exit
fi

LG=$1
DUT=$2

echo "free hosts if still allocated by someone else, keeping your calender entry"
pos allocations free "$LG" -k
pos allocations free "$DUT" -k

echo "allocate hosts"
POS_OUTPUT=`pos allocations allocate "$LG" "$DUT" --result-folder component-test/{{ experiment_name }}`
RESULT_DIR=`echo ${POS_OUTPUT} | awk '{print $NF}'`
echo ${RESULT_DIR} >> ${ROOT}/result_directory.txt

echo "set images to debian buster"
pos nodes image "$LG" debian-buster
pos nodes image "$DUT" debian-buster

echo "load variables files"
pos allocations variables "$LG" ${EXP}/lg/variables.yml
pos allocations variables "$DUT" ${EXP}/dut/variables.yml
# default (for all hosts) variables file
pos allocations variables "$LG" ${EXP}/global-variables.yml --as-global
# loop variables for experiment script
pos allocations variables "$LG" ${EXP}/loop-variables.yml --as-loop

echo "set bootparameters"
{% for boot in bootparameters %}pos nodes bootparameter "{{ boot.device }}" {{ boot.parameters }}
{% endfor %}

#echo "bootstrapping nodes"
#{ pos nodes boots "$LG"; echo "$LG bootstrapped successfully"; } &
#{ pos nodes boots "$DUT"; echo "$DUT bootstrapped successfully"; } &
#wait

echo "reboot experiment hosts..."
# run reset blocking in background and wait for processes to end before continuing
{ pos nodes reset "$LG"; echo "$LG booted successfully"; } &
{ pos nodes reset "$DUT"; echo "$DUT booted successfully"; } &
wait

echo "copying supplementary files required for setup"
{% for cp in copy_setup %}{ pos nodes copy "{{ cp.device }}" ${ROOT}/{{ cp.from }} --dest {{ cp.dest }}; } &{% if loop.index % 10 == 9 %}
wait{% endif %}
{% endfor %}
wait

echo "setup experiment hosts..."
{ pos commands launch --name setup --infile ${EXP}/lg/setup.sh --blocking "$LG"; echo "$LG setup done"; } &
{ pos commands launch --name setup --infile ${EXP}/dut/setup.sh --blocking "$DUT"; echo "$DUT setup done"; } &
wait

echo "copying supplementary files"
{% for cp in copy %}{ pos nodes copy "{{ cp.device }}" ${ROOT}/{{ cp.from }} --dest {{ cp.dest }}; } &{% if loop.index % 10 == 9 %}
wait{% endif %}
{% endfor %}
wait

echo "execute experiment on hosts..."
{ pos commands launch --name measurement --infile ${EXP}/lg/measurement.sh --blocking --loop "$LG"; } &
{ pos commands launch --name measurement --infile ${EXP}/dut/measurement.sh --blocking --loop "$DUT"; } &
wait

echo "free hosts, end calendar entry"
#pos allocations free "$1" -k

cd ${EVALUATION}
echo "compress data"
bash compress_data.sh ${RESULT_DIR}

echo "perform evaluation"
bash setup_evaluation.sh
bash run_evaluation.sh

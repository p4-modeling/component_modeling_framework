#! /bin/bash

{% if testbed_manual %}
# NOTE: this script is written to work with the pos testbed controller
# these are the steps required to perform the measurement
# to work in another testbed, replace the pos_* calls with respective implementations
{% endif %}

set -x

REPEAT_MAX_LOAD=$(pos_get_variable --from-global repeat_max_load)
CORES=$(pos_get_variable --from-loop cpu_cores)
P4_PROGRAM=synthetic

# perf
PERF_STAT_RUNS=$(pos_get_variable perf/runs)
PERF_STAT_EVENTS=$(pos_get_variable perf/events)
DURATION_MAX_LOAD=$(pos_get_variable duration/max_load --from-global)
PERF_STAT_DURATION=`python -c "print(int((${DURATION_MAX_LOAD} - 2)/${PERF_STAT_RUNS}))"`

{% if scale_frequency %}
# set cpu frequency
FREQ=$(pos_get_variable --from-loop cpu_frequency)
cpupower --cpu all frequency-set --freq ${FREQ}GHz
{% endif %}

# source t4p4s variables
source /root/t4p4s/t4p4s_environment_variables.sh

# run t4p4s
cd /root/t4p4s/t4p4s/

{% if multiple_programs %}
# use correct program and controller
INDEX=$(pos_get_variable --from-loop {{ multiple_programs }})
cp examples/synthetic_${INDEX}.p4 examples/synthetic.p4
cp src/hardware_dep/shared/ctrl_plane/dpdk_l2fwd_controller_${INDEX}.c src/hardware_dep/shared/ctrl_plane/dpdk_l2fwd_controller.c
{% endif %}
{% if update_controlplane %}
cp src/hardware_indep/controlplane_${INDEX}.c.py src/hardware_indep/controlplane.c.py
{% endif %}

for (( REPETITION=1; REPETITION<=$REPEAT_MAX_LOAD; REPETITION++ ))
do
	# clear startup state
	pos_set_variable tapas_started 0
	# start t4p4s
	pos_run tapas_${REPETITION} --loop -- ./t4p4s.sh :${P4_PROGRAM} cores=${CORES} ports=2x${CORES}
	
	# wait for startup
	MAX_WAIT=15
	{% if increase_max_wait %}
	MAX_WAIT=$INDEX
	{% endif %}
	if [[ $MAX_WAIT -lt 15 ]]; then
		MAX_WAIT=15
	fi
	for ((i = 0 ; i <= $MAX_WAIT ; i++));
	do
	        if [[ $(pos_get_variable tapas_started) == '1' ]]; then
	                echo 'finished compiling'
	                break
	        fi
	        echo "waiting for compiling end"
	        sleep 1
	done

	# wait some more time until app started
	sleep 5
	{% if increase_wait %}
	# wait per table entry
	CONTROLLER_STARTUP=`python -c "print(${INDEX} / 1000000)"`
	echo "waiting an additional ${CONTROLLER_STARTUP} seconds"
	sleep ${CONTROLLER_STARTUP}
	{% endif %}
	
	pos_sync --loop --tag dut_startup_${REPETITION}_completed
	# wait for moongen to start
	pos_sync --loop --tag max_load_measurement_${REPETITION}_started
	# start perf stat recording
	sleep 1
	pos_run perf_stat_${REPETITION} --upload --loop bash /root/run_perf_stat_${CORES}.sh $PERF_STAT_RUNS $PERF_STAT_EVENTS $PERF_STAT_DURATION
	pos_sync --loop --tag max_load_measurement_${REPETITION}_finished

	# stop if we restart afterwards
	if [ "$REPETITION" -ne "$REPEAT_MAX_LOAD" ]
	then
		pos_kill tapas_${REPETITION} --loop
		killall ${P4_PROGRAM}
		pkill -f "./src/hardware_dep/shared/ctrl_plane/dpdk_l2fwd_controller"
	fi
done

# wait for measurement to finish
pos_sync --loop --tag loadgen_measurement_finished

# finally stop t4p4s
pos_kill tapas_${REPEAT_MAX_LOAD} --loop
killall ${P4_PROGRAM}
pkill -f "./src/hardware_dep/shared/ctrl_plane/dpdk_l2fwd_controller"


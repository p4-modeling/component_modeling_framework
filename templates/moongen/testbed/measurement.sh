#! /bin/bash

{% if testbed_manual %}
# NOTE: this script is written to work with the pos testbed controller
# these are the steps required to perform the measurement
# to work in another testbed, replace the pos_* calls with respective implementations
{% endif %}

set -x

DURATION_STARTUP=5
DURATION_MAX_LOAD=$(pos_get_variable duration/max_load --from-global)
DURATION_LATENCY=$(pos_get_variable duration/latency --from-global)
REPEAT_MAX_LOAD=$(pos_get_variable --from-global repeat_max_load)

{% if scale_packet_size %}
PACKET_SIZE=$(pos_get_variable packet_size --from-loop)
{% else %}
PACKET_SIZE=$(pos_get_variable packet_size)
{% endif %}

{% if measure_latency %}
{% if scale_load %}
# we measure not at the relative loads, but at the full load as specified
LATENCY_RATE=$(pos_get_variable load_rate --from-loop)
{% else %}
# we measure for the three relative latency loads
LATENCY_RATES=$(pos_get_variable latency_rates --from-global)
{% endif %}
{% endif %}

{% if scale_table_entries %}
TABLE_ENTRIES=$(pos_get_variable table_entries --from-loop)
{% endif %}

RX_PORT=$(pos_get_variable port/rx)
TX_PORT=$(pos_get_variable port/tx)


# start max load test
for (( REPETITION=1; REPETITION<=$REPEAT_MAX_LOAD; REPETITION++ ))
do
	# wait for dut to start up
	pos_sync --loop --tag dut_startup_${REPETITION}_completed

	pos_run lg_max_load_${REPETITION} --loop -- /root/moongen/build/MoonGen /root/max-load.lua ${TX_PORT} ${RX_PORT} {% if scale_table_entries %}-t ${TABLE_ENTRIES}{% endif %} --pktsize ${PACKET_SIZE}
	sleep ${DURATION_STARTUP}
	pos_sync --loop --tag max_load_measurement_${REPETITION}_started
	sleep ${DURATION_MAX_LOAD}
	pos_kill lg_max_load_${REPETITION} --loop

	# notify end
	pos_sync --loop --tag max_load_measurement_${REPETITION}_finished

	# upload data
	mv throughput-rx.csv throughput-max-rx.csv_${REPETITION}
	mv throughput-tx.csv throughput-max-tx.csv_${REPETITION}
	pos_upload --loop throughput-max-rx.csv_${REPETITION}
	pos_upload --loop throughput-max-tx.csv_${REPETITION}
done

{% if measure_latency %}
# determine max rate
MAX_RATE=$(python3 get_max_rate.py)

{% if scale_load %}
       LG_NAME="lg_rate"
       RATE=$(python3 multiply_floats.py ${LATENCY_RATE} ${MAX_RATE})
       multiplier="rate"
{% else %}
for multiplier in ${LATENCY_RATES}
do
       LG_NAME="lg_rate_${multiplier}"
       RATE=$(python3 multiply_floats.py ${multiplier} ${MAX_RATE})
{% endif %}
       echo "rate is ${RATE}"

       pos_run ${LG_NAME} --loop -- /root/moongen/build/MoonGen /root/latency.lua ${TX_PORT} ${RX_PORT} -p ${RATE} {% if scale_table_entries %}-t ${TABLE_ENTRIES}{% endif %} --pktsize ${PACKET_SIZE}
       sleep ${DURATION_STARTUP}
       sleep ${DURATION_LATENCY}
       pos_kill ${LG_NAME} --loop
       # upload data
       pos_upload --loop throughput-rx.csv --outfile throughput-${multiplier}-rx.csv
       pos_upload --loop throughput-tx.csv --outfile throughput-${multiplier}-tx.csv
       pos_upload --loop histogram.csv --outfile histogram-${multiplier}.csv
{% if not scale_load %}
done
{% endif %}
{% endif %}

# inform that measurement has finished
pos_sync --loop --tag loadgen_measurement_finished

pos_heartbeat -m 15

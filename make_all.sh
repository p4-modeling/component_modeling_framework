#! /bin/bash

TEST_NODES=sample_nodes

./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments baseline --load
./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments baseline --cpu-frequency

./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments mat --number-of-entries-exact
./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments mat --number-of-entries-ternary
./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments mat --number-of-entries-lpm

./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments mat --number-of-match-keys-exact
./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments mat --number-of-match-keys-ternary

./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments mat --number-action-data

./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments mat --number-of-tables-exact
./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments mat --number-of-same-tables-exact
./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments mat --number-of-tables-lpm
./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments mat --number-of-tables-ternary

./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments parser --added-headers
./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments parser --removed-headers
./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments parser --added-headers-size

./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments parser --number-of-parsed-fields

./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments other --number-of-header-field-writes
./generate_component_benchmark.py --test-nodes ${TEST_NODES} p4_t4p4s pos experiments other --number-of-meta-field-writes

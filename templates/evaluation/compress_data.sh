#!/bin/bash

set -x

ORIG_DIR=`pwd`
RESULT_DIR=${1}

if [ -z "$RESULT_DIR" ]
then
	echo "No result dir, using last result directory"
	RESULT_DIR=$( tail -n 1 ../result_directory.txt )
fi

PARENT_DIR=`python -c "print('/'.join('${RESULT_DIR}'.split('/')[:-1]))"`
EXP_DIR=`python -c "print('${RESULT_DIR}'.split('/')[-1])"`

cd ${PARENT_DIR}

set +x
tar --zstd -cf ${EXP_DIR}.tar.zst ${EXP_DIR}/cesis/perf*.stderr \
	${EXP_DIR}/nida/throughput* \
	${EXP_DIR}/nida/histogram* \
	${EXP_DIR}/cesis/*.loop \
	${EXP_DIR}/nida/*.loop \
	${EXP_DIR}/config
set -x

cd ${ORIG_DIR}
mv ${PARENT_DIR}/${EXP_DIR}.tar.zst ../{{ data_dir }}

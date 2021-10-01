#!/bin/bash

set -euo pipefail

TARGETS_DIR=`pwd`/fuzzwatch_targets
PROJ=$TARGETS_DIR/cjson 
INPUT_DIR=$PROJ/input
OUTPUT_DIR=$PROJ/output
TARGET=$PROJ/build/cjson_read
CONFIG=$PROJ/manul.config

if [ ! -f $TARGET ]
then
    cd $TARGETS_DIR
    ./pull_and_build_cjson.sh
    cd ..
fi

rm -rf $OUTPUT_DIR
mkdir $OUTPUT_DIR
sleep 0.1

set -x

python ./manul.py -i $INPUT_DIR -o $OUTPUT_DIR -c $CONFIG "$TARGET @@"

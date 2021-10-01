#!/bin/bash

set -euo pipefail

TARGETS_DIR=`pwd`/fuzzwatch_targets
PROJ=$TARGETS_DIR/tinyxml2
INPUT_DIR=$PROJ/input
#INPUT_DIR=$PROJ/input-utf8
OUTPUT_DIR=$PROJ/output
TARGET=$PROJ/build/xmltest
CONFIG=$PROJ/manul.config

if [ ! -f $TARGET ]
then
    cd $TARGETS_DIR
    ./pull_and_build_tinyxml2.sh
    cd ..
fi

rm -rf $OUTPUT_DIR
mkdir $OUTPUT_DIR
sleep 0.1

set -x

python ./manul.py -i $INPUT_DIR -o $OUTPUT_DIR -c $CONFIG "$TARGET @@"

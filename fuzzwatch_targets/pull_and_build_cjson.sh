#!/bin/bash

# For testing FuzzWatch: build cjson with AFL instrumentation

TARGET_DIR=`pwd`/cjson
OUT=$TARGET_DIR/build
SRC=$TARGET_DIR/cJSON

# Prep the target directory
cd $TARGET_DIR
rm -rf $OUT
mkdir $OUT

# Pull the source
if [ ! -d $SRC ]
then
    git clone https://github.com/DaveGamble/cJSON.git
fi

# Build the fuzz target
cd $SRC
THEIR_DIR=./fuzzing
THEIR_BUILD=afl-build

cd $THEIR_DIR

rm -rf $THEIR_BUILD
mkdir -p $THEIR_BUILD
cd $THEIR_BUILD

CC=afl-clang-fast cmake ../.. -DENABLE_FUZZING=On -DENABLE_SANITIZERS=On -DBUILD_SHARED_LIBS=Off
make afl-main

# Copy target to our build
cp fuzzing/afl-main $OUT/cjson_read

# Populate template config with absolute paths
CONFIG=$TARGET_DIR/manul.config
cat $TARGET_DIR/manul_template.config > $CONFIG
echo "dict = $TARGET_DIR/json.dict" >> $CONFIG

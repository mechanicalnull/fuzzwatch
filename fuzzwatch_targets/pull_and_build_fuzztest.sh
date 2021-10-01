#!/bin/bash

# For testing FuzzWatch: build cjson with AFL instrumentation
TARGET_DIR=`pwd`/fuzztest
BUILD=$TARGET_DIR/build

# Prep the target directory
cd $TARGET_DIR
rm -rf $BUILD
mkdir $BUILD

# Build the fuzz target
afl-clang-fast fuzztest.c -g -o $BUILD/fuzztest

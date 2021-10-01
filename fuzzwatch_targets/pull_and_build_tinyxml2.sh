#!/bin/bash

# For testing FuzzWatch: build tinyxml2 with AFL instrumentation

TARGET_DIR=`pwd`/tinyxml2
BUILD=$TARGET_DIR/build
SRC=tinyxml2
CXX=afl-clang-fast++

set -e

# Prep the target directory
cd $TARGET_DIR
rm -rf $BUILD
mkdir $BUILD

# Pull the source
if [ ! -d $SRC ]
then
    git clone https://github.com/leethomason/tinyxml2.git $SRC
    # Pulling an old version for demonstration/testing purposes
    cd $SRC
    git checkout -q 686ef404b8718ab4fa40c2f10633a1f69375c20d
    cd ..
fi

# Build the target
cd $SRC
$CXX xmltest.cpp tinyxml2.cpp -o $BUILD/xmltest
file $BUILD/xmltest

# Populate template config with absolute paths
CONFIG=$TARGET_DIR/manul.config
cat $TARGET_DIR/manul_template.config > $CONFIG
echo "dict = $TARGET_DIR/xml.dict" >> $CONFIG

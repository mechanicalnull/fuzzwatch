#!/bin/bash

# For testing FuzzWatch: build ffmpeg with AFL instrumentation

# Dependencies noted on Ubuntu 20.04:
# nasm libass-dev libmp3lame-dev libopus-dev libvorbis-dev libx264-dev
# libx265-dev

TARGET_DIR=`pwd`/ffmpeg
BUILD=$TARGET_DIR/build
SRC=ffmpeg
CC=afl-clang-fast
CXX=afl-clang-fast++

set -e

cd $TARGET_DIR
rm -rf $BUILD
mkdir $BUILD

if [ ! -d $SRC ]
then
    git clone --depth=1 https://github.com/FFmpeg/FFmpeg.git $SRC
fi

cd $SRC

echo "[*] Heads up, this build can take a while; maybe go grab a coffee or something..."

# Configure and build
./configure \
    --pkg-config-flags="--static" \
    --extra-libs="-lpthread -lm" \
    --bindir="$SRC/bin" \
    --enable-gpl --enable-libass --enable-libfreetype --enable-libmp3lame \
    --enable-libopus --enable-libvorbis --enable-libx264 --enable-nonfree \
    --cc=$CC --cxx=$CXX \
    --extra-cflags="-O1 -fno-omit-frame-pointer -g" \
    --extra-cxxflags="-O1 -fno-omit-frame-pointer -g" \
    --disable-stripping \
    --enable-debug

AFL_HARDEN=1 make -j8

cp ffmpeg $BUILD/

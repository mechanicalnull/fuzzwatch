FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
        vim \
        git wget \
        clang-11 llvm-11 \
        afl++-clang \
        python3 python-is-python3 python3-pip python3-dev \
        python3-tk \
        build-essential make automake cmake ninja-build \
        nasm  \
        libass-dev libmp3lame-dev libopus-dev libvorbis-dev \
        libx264-dev libx265-dev \
        locales locales-all
# NOTE: Python3 packages and AFL are the only FuzzWatch deps.
#       Most of the packages are for building other targets.
#       All of the packages after python3-tk are for ffmpeg.

# This prevents some distracting locale warnings in ffmpeg's build
RUN echo "LC_ALL=en_US.UTF-8" >> /etc/environment && \ 
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \ 
    echo "LANG=en_US.UTF-8" > /etc/locale.conf && \ 
    locale-gen en_US.UTF-8


WORKDIR /src/

# Installing AFL from package to save electricity, do this to pull from git
#RUN apt-get install -y 
#        bison flex \
#        libtool libtool-bin \
#        libssl-dev libffi-dev libglib2.0-dev libpixman-1-dev
#RUN git clone https://github.com/AFLplusplus/AFLplusplus.git afl && \
#    cd afl && \
#    update-alternatives --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-11 50 && \
#    make && make install


RUN git clone https://github.com/mechanicalnull/fuzzwatch.git

WORKDIR /src/fuzzwatch

RUN pip3 install -r requirements.txt

RUN cd fuzzwatch_targets && \
    ./pull_and_build_fuzztest.sh


# Fuzzwatch

![GUI Clip](misc/fuzzwatch_ui.gif?raw=true "Screencap of Fuzzwatch in action")

Fuzzwatch is a Python GUI made to show what's going on inside of a fuzzer.
It is currently integrated with [Manul](https://github.com/mxmssh/manul), which
is a coverage-guided fuzzer modeled after AFL and written entirely in Python.
While Manul has cross-platform support, Fuzzwatch is only tested on Linux.

## Quick Start

The following snippet installs the requirements, builds the included toy
program, and runs the fuzzer. It finds a crash in under 5 minutes on my laptop.

```bash
git clone https://github.com/mechanicalnull/fuzzwatch
cd fuzzwatch
pip install -r requirements.txt
# This script builds an example target. It assumes you have afl-clang-fast,
# you can do `apt install -y afl++-clang` or similar if needed
./run_fuzzwatch_fuzztest.sh
```

Scripts for building and running example targets are included: 
`run_fuzzwatch_*.sh`.

## Installing

There shouldn't be many non-Python dependencies of Fuzzwatch itself, but a
Dockerfile is included to show a clean Ubuntu build.

If you want to run Fuzzwatch from inside the container, you'll need to pass an
X11 unix socket into the container and disable access control. There are other
access mechanisms in the xhost manpage, but for compatibility and ease-of-use,
we disable it in this example.

```bash
xhost +
docker build -t mechanicalnull/fuzzwatch .
docker run -it --rm \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY=unix$DISPLAY \
    mechanicalnull/fuzzwatch ./run_fuzzwatch_fuzztest.sh
xhost -
```
## About Fuzzwatch

Fuzzwatch is strictly for demonstration/learning purposes. Fuzzers don't
normally show this kind of detailed information because it's inefficient to
expose it, and slowing down a fuzzer just to display more stats makes the fuzzer
less effective.

Fuzzwatch's design is "in the loop" so it can get precise information and even
control the fuzzer if needed, rather than a more efficient polling method. So
instead of wrestling to make Fuzzwatch efficient, we embrace it; enjoying the
simplicity of fuzzing at a more deliberate pace on a single core.

The two obvious graphical additions are the depiction of the current mutation in
realtime and the display of AFL-style coverage bitmaps. The current mutation is
self-explanatory, but hopefully the bitmaps are interesting if you've never
thought about how a coverage-guided fuzzer like Manul or AFL understands
coverage and makes progress. The idea is that by seeing different aspects of a
fuzzer which are not often exposed, we can increase our understanding and ask
better questions about how to improve fuzzers.

### New Files/Changes

You can see all of the Fuzzwatch modifications to Manul with one git command:

```bash
git diff f525df HEAD
```

The primary fuzzwatch files are the frontend code (`fuzzwatch.py`) and the
shared state that the fuzzer writes to and the frontend code reads from
(`fuzzwatch_state.py`). Designing it in this way should make it easier to adapt
Fuzzwatch to other fuzzers, though I wasn't strict about keeping things loosely
coupled.

Modifications had to be made to the mutators in Manul in order to expose
information about the current mutation and pass it into the shared state
(`manul_afl.py`), and the bitmaps also needed to be sync'd with the shared GUI
state (`manul.py`). Lastly, we borrow the statistic calculations and pass those
into the shared state (`printing.py`).

## Future Work

I don't know how useful this will be, so please open an issue for feature
requests or take the initiative and submit a PR implementing it ;)

- Integrate Fuzzwatch into AFL++ to show differences between fuzzers
- Add "Pause", "Slow", "Slower", "Very Slow" buttons that stop/slow the fuzzer
- Implement a color bar for the bitmaps to show how many bits are set in a byte,
  without losing precision or ability to effectively depict a sparse bitmap
- Add a histogram to show number of mutations applied to each input

## Shout Out

Thanks to [@mxmssh](https://github.com/mxmssh) for writing Manul (especially in
Python) and for putting a GIF of mutations up on Twitter that initially inspired
this project.

Reach out to me on Twitter
([@mechanicalnull](https://twitter.com/mechanicalnull)) if you think this is
useful, or if you plan to use this for teaching and want some discussion
questions.

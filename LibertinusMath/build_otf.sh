#!/bin/env bash

set -e
mkdir -p build

# `features/` is a pristine upstream snapshot, so copy it to build/ with the patched
# feature files substituted in, and let `pcpp` resolve the `#include`s out of the copy.
python -c 'import patches; patches.patch_features("features", "build/features")'

# Resolve the feature file's `#ifdef MATH` includes, for build.py to merge.
pcpp --line-directive -D MATH -I build/features -o build/gsub.fea build/features/gsub.fea

python build.py LibertinusMath-Regular.sfd build/gsub.fea build/LibertinusMath-Regular-instance.otf

# Before hinting, so psautohint and cffsubr do not work on glyphs that get thrown away.
python prune.py build/LibertinusMath-Regular-instance.otf build/LibertinusMath-Regular-pruned.otf

psautohint -o build/LibertinusMath-Regular-instance-hinted.otf build/LibertinusMath-Regular-pruned.otf
python -m cffsubr -o build/LibertinusMath-Regular-subr.otf build/LibertinusMath-Regular-instance-hinted.otf
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python gftools fix-font build/LibertinusMath-Regular-subr.otf -o LibertinusMath-Regular.otf
font-v write --ver=7-051 --dev --sha1 LibertinusMath-Regular.otf

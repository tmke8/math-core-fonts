#!/bin/bash
set -euo pipefail

# NotoSansMath-Regular.ufo is a pristine upstream snapshot; the browser-compatibility
# patches are applied to a copy of it, which is also what makes them inspectable:
# `diff -r NotoSansMath-Regular.ufo build/NotoSansMath-Regular.ufo`.
rm -rf build
mkdir build
cp -r NotoSansMath-Regular.ufo build/
python patches.py build/NotoSansMath-Regular.ufo

fontmake --output-path NotoSansMath-Regular.otf -o otf -u build/NotoSansMath-Regular.ufo --filter ... --filter FlattenComponentsFilter --filter DecomposeTransformedComponentsFilter

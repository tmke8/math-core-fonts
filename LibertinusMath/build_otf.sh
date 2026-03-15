#!/bin/env bash

set -e
mkdir -p build
sfdnormalize LibertinusMath-Regular.sfd build/LibertinusMath-Regular-normalized.sfd

#sfd2ufo build/LibertinusMath-Regular-normalized.sfd build/LibertinusMath-Regular-normalized.ufo
#ufonormalizer build/LibertinusMath-Regular-normalized.ufo
#fontmake --verbose WARNING --fea-include-dir features -u build/LibertinusMath-Regular-normalized.ufo -o otf --output-dir build
#mv build/LibertinusMath-Regular-normalized.otf build/LibertinusMath-Regular-instance.otf

python build.py --input=build/LibertinusMath-Regular-normalized.sfd --output=build/LibertinusMath-Regular-instance.otf --feature-file=features/gsub.fea

psautohint -o build/LibertinusMath-Regular-instance-hinted.otf build/LibertinusMath-Regular-instance.otf
python -m cffsubr -o build/LibertinusMath-Regular-subr.otf build/LibertinusMath-Regular-instance-hinted.otf
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python gftools fix-font build/LibertinusMath-Regular-subr.otf -o build/LibertinusMath-Regular.otf
font-v write --ver=7-051 --dev --sha1 build/LibertinusMath-Regular.otf

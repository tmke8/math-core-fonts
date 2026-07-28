#!/bin/bash

fontforge -lang=py -script - <<'EOF'
import os
import sys

sys.path.insert(0, os.getcwd())  # the script is read from stdin, so there is no __file__

import fontforge

from patches import apply_patches

font = fontforge.open("NewCMMath-Book.sfd")
apply_patches(font)
font.generate("NewCMMath-Book.otf")
EOF

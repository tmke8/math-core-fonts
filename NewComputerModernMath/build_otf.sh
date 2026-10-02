#!/bin/bash

set -e

python3 - <<'EOF'
import fontforge

from patches import apply_patches

font = fontforge.open("NewCMMath-Book.sfd")
apply_patches(font)
font.generate("NewCMMath-Book.otf")
EOF

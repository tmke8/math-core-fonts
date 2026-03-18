#!/bin/bash

fontforge -lang=py -script - <<'EOF'
import fontforge

font = fontforge.open("NewCMMath-Book.sfd")
font.generate("NewCMMath-Book.otf")
EOF

#!/bin/bash

fontforge -lang=py <<'EOF'
import fontforge

font = fontforge.open("NewCMMath-Book.sfd")
font.generate("NewCMMath-Book.otf")
EOF

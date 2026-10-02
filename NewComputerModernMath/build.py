"""Build NewCMMath-Book.otf.

    uv run python NewComputerModernMath/build.py

Only FontForge's `fontforge` module is needed, so any `python3` that can import it will do,
inside the project venv or not.
"""

import os
from pathlib import Path

import fontforge

from patches import apply_patches


def main():
    os.chdir(Path(__file__).resolve().parent)
    font = fontforge.open("NewCMMath-Book.sfd")
    apply_patches(font)
    font.generate("NewCMMath-Book.otf")


if __name__ == "__main__":
    main()

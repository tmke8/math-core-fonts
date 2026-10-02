"""Build NotoSansMath-Regular.otf.

    .venv/bin/python NotoSansMath/build.py

NotoSansMath-Regular.ufo is a pristine upstream snapshot; the browser-compatibility
patches are applied to a copy of it, which is also what makes them inspectable:
`diff -r NotoSansMath-Regular.ufo build/NotoSansMath-Regular.ufo`.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from ufoLib2 import Font

from patches import apply_patches

UFO = "NotoSansMath-Regular.ufo"


def main():
    os.chdir(Path(__file__).resolve().parent)
    shutil.rmtree("build", ignore_errors=True)
    shutil.copytree(UFO, f"build/{UFO}")

    font = Font.open(f"build/{UFO}")
    apply_patches(font)
    font.save()

    subprocess.run([
        sys.executable, "-m", "fontmake",
        "--output-path", "NotoSansMath-Regular.otf", "-o", "otf", "-u", f"build/{UFO}",
        "--filter", "...",
        "--filter", "FlattenComponentsFilter",
        "--filter", "DecomposeTransformedComponentsFilter",
    ], check=True)


if __name__ == "__main__":
    main()

"""Build LibertinusMath-Regular.otf, leaving every intermediate in `build/`.

    uv run python LibertinusMath/build.py

The stages:

1. `patches.patch_features()` copies `features/`, a pristine upstream snapshot, to
   `build/features/` with the patched feature files substituted in.
2. pcpp resolves the `#include`s and `#ifdef MATH`s of the copy's `gsub.fea` into
   `build/gsub.fea`.
3. `to_otf()` opens the `.sfd`, patches it, merges the features and generates the unhinted
   `build/…-instance.otf`.
4. `prune()` drops the glyphs nothing can reach. It runs before hinting, so that psautohint
   and cffsubr do not work on glyphs that get thrown away.
5. psautohint, cffsubr and `gftools fix-font`; then font-v stamps the version.
"""

import os
import subprocess
import sys
from pathlib import Path

from pcpp import Preprocessor

import patches
from prune import prune
from to_otf import to_otf

NAME = "LibertinusMath-Regular"
VERSION = "7-051"


def preprocess(source, output, include_dir):
    """Do what `pcpp -D MATH -I <include_dir>` does, without `#line` markers."""
    preprocessor = Preprocessor()
    preprocessor.line_directive = None
    preprocessor.define("MATH 1")
    preprocessor.add_path(include_dir)
    with open(source) as f:
        preprocessor.parse(f)
    with open(output, "w") as f:
        preprocessor.write(f)


def run(module, *args, env=None):
    """Run a tool's command-line entry point under this interpreter."""
    command = [sys.executable, "-m", module, *args]
    subprocess.run(command, check=True, env=os.environ | (env or {}))


def main():
    os.chdir(Path(__file__).resolve().parent)
    os.makedirs("build", exist_ok=True)

    patches.patch_features("features", "build/features")
    preprocess("build/features/gsub.fea", "build/gsub.fea", "build/features")
    to_otf(f"{NAME}.sfd", "build/gsub.fea", f"build/{NAME}-instance.otf")
    prune(f"build/{NAME}-instance.otf", f"build/{NAME}-pruned.otf")

    run("psautohint", "-o", f"build/{NAME}-hinted.otf", f"build/{NAME}-pruned.otf")
    run("cffsubr", "-o", f"build/{NAME}-subr.otf", f"build/{NAME}-hinted.otf")
    run("gftools.scripts.fix_font", f"build/{NAME}-subr.otf", "-o", f"{NAME}.otf",
        env={"PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION": "python"})
    run("fontv.app", "write", f"--ver={VERSION}", "--dev", "--sha1", f"{NAME}.otf")


if __name__ == "__main__":
    main()

"""Browser-compatibility patches applied to the pristine upstream Libertinus Math sources.

`LibertinusMath-Regular.sfd` and `features/` in this directory are an unmodified upstream
snapshot; every deviation from upstream lives here and is re-applied at build time (see
`build_otf.sh`). Re-vendoring upstream is therefore a plain file replacement. See the repo
`README.md` for why each patch is needed.

No patch alters a curve: they copy an existing glyph onto another glyph, translate an
outline within glyph space, or change an advance width.

There are two halves:

* `apply_patches(font)` runs inside FontForge over the opened `.sfd` (`build.py`).
* `patch_features(src, dst)` is plain Python and rewrites the `.fea` sources into a build
  directory before `pcpp` sees them (`build_otf.sh`). It only imports the standard library
  so both interpreters can load this module.

Every operation is relative to the glyph's own bounding box or to another glyph's metrics,
so the tables are just lists of glyph names: no coordinate is written down here, and
nothing has to be re-measured if upstream redraws or repositions something.
"""

import os
import shutil

# ---------------------------------------------------------------------------
# Feature files
# ---------------------------------------------------------------------------
#
# Two GSUB changes cannot sensibly be expressed as Python, so they are kept as feature
# files next to the upstream ones and swapped in at build time:
#
# * `ss09` is a new feature that maps the primes to their raised, script-sized `.ssty1`
#   variants. The prime patch for this font is a feature rather than a glyph swap (unlike
#   NewCM and Noto), because Libertinus already ships the `.ssty1` outlines.
# * `ssty` is upstream's, extended: it gains U+2057 (which upstream omits) and the Latin,
#   bold and bold-digit alphabets.
#
# `features/gsub.fea` `#include`s `ssty.fea` under `#ifdef MATH`, and that is where both
# features want to live, so the two replacement files are concatenated over it.
FEATURE_REPLACEMENTS = {
    "ssty.fea": ("ss09.fea.new", "ssty.fea.new"),
}

# ---------------------------------------------------------------------------
# Glyph patches
# ---------------------------------------------------------------------------

# 1. Slanted stretched integrals by default.
#
# Upstream draws the stretched (`.size1`) integrals upright and keeps the slanted forms —
# the shape TeX and every other math font use — behind the `ss08` feature, which browsers
# do not turn on. Copy each `X.slsize1` over `X.size1` so the stretched integral is slanted
# out of the box. `ss08` still works; it now substitutes glyphs identical to its inputs.
SLANTED_INTEGRALS = [
    "integral",  # U+222B
    "uni222C",   # U+222C double integral
    "uni222D",   # U+222D triple integral
    "uni222E",   # U+222E contour integral
    "uni222F",   # U+222F surface integral
    "uni2230",   # U+2230 volume integral
    "uni2231",   # U+2231 clockwise integral
    "uni2232",   # U+2232 clockwise contour integral
    "uni2233",   # U+2233 anticlockwise contour integral
    "uni2A0C",   # U+2A0C quadruple integral
]

# 2. Stretched integrals centred on the math axis.
#
# Upstream centres them on (ascender − descender) / 2, which leaves them sitting visibly
# high next to the fraction bars and relations they are drawn against. Move the family down
# so that the middle of the plain integral lands on `MATH:AxisHeight`. The whole family
# shifts by that one amount — the glyphs are drawn to line up with each other, and the ones
# carrying an arrow have a taller bounding box than the rest. Only the glyphs that own
# outlines are listed; the others are references to these and follow along.
AXIS_CENTRED_ON = "integral.slsize1"
AXIS_CENTRED_INTEGRALS = [
    AXIS_CENTRED_ON,
    "uni222E.slsize1",
    "uni222F.slsize1",
    "uni2230.slsize1",
    "uni2231.slsize1",
    "uni2232.slsize1",
    "uni2233.slsize1",
]

# 3. RATIO spacing.
#
# U+2236 RATIO is two `period`s stacked, but upstream gives it a 527-unit advance — more
# than twice `colon`'s — so `a ∶ b` comes out with a gap on either side. Give it `colon`'s
# advance width and left side bearing; the vertical placement of the dots is untouched.
RATIO_METRICS_FROM = {"uni2236": "colon"}

# 4. Accent centering (Chromium, WebKit).
#
# These three have no non-combining code point, so browsers place them as standalone
# accents and get the horizontal position wrong. Centre the outline on x=0 — that is where
# a combining mark's zero-width advance leaves the pen. `uni20D7` is the odd one out in
# having a 420-unit advance, and is centred the same way regardless.
CENTERED = [
    "uni20D7",  # combining right arrow above (\vec)
    "uni20DB",  # combining three dots above (\dddot)
    "uni20DC",  # combining four dots above (\ddddot)
]

# 5. Accent lowering (WebKit).
#
# Safari renders <mover accent="true"> as-is, so the empty space an accent normally carries
# above the baseline becomes a gap between the base letter and its accent. Drop each accent
# so that its lowest point sits exactly on the baseline.
LOWERED = [
    "grave",       # U+0060
    "acute",       # U+00B4
    "circumflex",  # U+02C6
    "tilde",       # U+02DC
    "macron",      # U+00AF
    "breve",       # U+02D8
    "dotaccent",   # U+02D9
    "dieresis",    # U+00A8
    "ring",        # U+02DA
    "caron",       # U+02C7
    "uni20D7",
    "uni20DB",
    "uni20DC",
]


def translate(glyph, dx, dy, move_references=True):
    """Move `glyph`, leaving its advance width alone.

    `Glyph.transform` shifts the advance width along with the outline, which is not what
    any of these patches want, so put the width back afterwards. `move_references` is False
    when the glyphs being referenced are moved by the same amount themselves, so that their
    offsets must stay where they are.
    """
    width = glyph.width
    flags = () if move_references else ("partialRefs",)
    glyph.transform((1, 0, 0, 1, dx, dy), flags)
    glyph.width = width


def copy_glyph(font, dest, src, rename):
    """Replace `dest` with `src`: both layers, its references, width and italic correction.

    `rename` maps a referenced glyph name onto the one `dest`'s copy should point at, so
    that the clone of a composite refers to clones rather than back into the source family.
    """
    source, target = font[src], font[dest]
    target.foreground = source.foreground
    target.background = source.background
    # The setter prepends, so hand it the list backwards to keep the source's order.
    target.references = tuple(
        (rename.get(name, name), transform)
        for name, transform, *_ in reversed(source.references))
    target.width = source.width
    target.italicCorrection = source.italicCorrection
    target.unlinkRmOvrlpSave = source.unlinkRmOvrlpSave


def axis_offset(font, name):
    # The glyph's own contours, not `glyph.boundingBox()`: every glyph in this family also
    # references others in it, and their outlines are not centred on the family's.
    _, ymin, _, ymax = font[name].foreground.boundingBox()
    return font.math.AxisHeight - (ymin + ymax) / 2


def centre_horizontally(font, name):
    """Centre the outline on x=0, taking its top-accent attachment with it.

    `MATH`'s `TopAccentHorizontal` is the point a renderer lines up over the base glyph, so
    it has to stay on the ink. Upstream keeps it at the midpoint of the outline, which is
    x=0 once the outline is centred there; `Glyph.transform` does not move it by itself.
    """
    glyph = font[name]
    xmin, _, xmax, _ = glyph.boundingBox()
    translate(glyph, -(xmin + xmax) / 2, 0)
    glyph.topaccent = 0


def lower_to_baseline(font, name):
    glyph = font[name]
    _, ymin, _, _ = glyph.boundingBox()
    translate(glyph, 0, -ymin)


def copy_metrics(font, dest, src):
    """Give `dest` `src`'s advance width and left side bearing."""
    source, target = font[src], font[dest]
    translate(target, source.boundingBox()[0] - target.boundingBox()[0], 0)
    target.width = source.width


def apply_patches(font):
    dy = axis_offset(font, AXIS_CENTRED_ON)
    for name in AXIS_CENTRED_INTEGRALS:
        translate(font[name], 0, dy, move_references=False)

    rename = {f"{n}.slsize1": f"{n}.size1" for n in SLANTED_INTEGRALS}
    for name in SLANTED_INTEGRALS:
        copy_glyph(font, f"{name}.size1", f"{name}.slsize1", rename)

    for dest, src in RATIO_METRICS_FROM.items():
        copy_metrics(font, dest, src)

    for name in CENTERED:
        centre_horizontally(font, name)

    for name in LOWERED:
        lower_to_baseline(font, name)


def patch_features(src, dst):
    """Copy the `features/` directory to `dst`, substituting the patched feature files.

    Run before `pcpp`, which resolves `gsub.fea`'s `#include`s out of whichever directory
    it is pointed at.
    """
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    # The `.new` files are sources for this function, not things `pcpp` should ever see.
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.new"))
    for name, parts in FEATURE_REPLACEMENTS.items():
        with open(os.path.join(dst, name), "w") as out:
            for part in parts:
                with open(os.path.join(src, part)) as f:
                    out.write(f.read())


if __name__ == "__main__":
    # Debugging aid: `fontforge -lang=py -script patches.py` writes the patched font back
    # out as an .sfd, so that
    #
    #     diff LibertinusMath-Regular.sfd LibertinusMath-Regular-patched.sfd
    #
    # shows the effect of the patches. A FontForge open/save round-trip is not quite
    # byte-identical here — upstream's file was written by an older FontForge — so the diff
    # also carries `ModificationTime`, `DisplaySize`/`AntiAlias`/`FitToEm`, a trailing space
    # on the `MATH:` entries that can take a device table, and a `VWidth:` line on each
    # touched glyph. None of that reaches the `.otf` (the build emits no `vhea`/`vmtx`). The
    # output is gitignored — it is a build artifact, not a source file.
    import fontforge

    font = fontforge.open("LibertinusMath-Regular.sfd")
    apply_patches(font)
    font.save("LibertinusMath-Regular-patched.sfd")

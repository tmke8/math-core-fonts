"""Browser-compatibility patches applied to the pristine upstream NotoSansMath-Regular.ufo.

The `.ufo` in this directory is an unmodified upstream snapshot; every deviation from
upstream lives here and is re-applied at build time by `build_otf.sh`, which patches a
copy under `build/` and hands that to fontmake. See the repo `README.md` for why each
patch is needed.

Usage: `python patches.py path/to/some.ufo` — patches the UFO in place.

No patch alters a curve: they copy an existing outline onto another glyph, scale a glyph
by the factor its own `ssty1` variant already used, translate outlines within glyph
space, or change an advance width.
"""

import re
import sys

from fontTools.misc.fixedTools import otRound
from ufoLib2 import Font
from ufoLib2.objects import Component

# 1. Primes always big.
#
# Browsers do not apply the `ssty` feature to primes, so U+2032 & friends render at full
# size where a raised, script-sized prime is wanted. Replace each base prime with the
# rendering of its own `.ssty1` variant — the exact glyph the `ssty` feature would have
# produced — and re-point the variants at the enlarged base so `ssty1`/`ssty2` still
# resolve to the sizes upstream intended.
PRIME_FAMILIES = [
    "prime",           # U+2032; must come first, the others are built from it
    "doubleprime",     # U+2033
    "tripleprime",     # U+2034
    "quadrupleprime",  # U+2057, a composite of four `prime` components
]

# 2. Non-combining accents that Unicode has but Noto does not draw.
#
# Browsers reach for the non-combining code point when an accent is used on its own, so
# add each one as a component of the combining glyph. `width` is the advance the accent
# gets; the outline is centered inside it below.
NEW_ACCENTS = {
    # name          source combining glyph  code point  advance
    "dieresis":    ("dieresiscomb",         0x00A8,     281),
    "macron":      ("macroncomb",           0x00AF,     377),
    "acute":       ("acutecomb",            0x00B4,     281),
    "caron":       ("caroncomb.s00",        0x02C7,     418),
    "breve":       ("brevecomb",            0x02D8,     418),
    "dotaccent":   ("dotaccentcomb",        0x02D9,     103),
    "smalltilde":  ("tildecomb.s00",        0x02DC,     367),
}

# `Aring` (U+00C5) is drawn as `A` plus the `ring` accent, so lowering `ring` would drag
# the ring down onto the A. `ringcomb` is the same outline in the same place, so point
# the composite at that instead and Å keeps rendering exactly as upstream drew it.
COMPOSITE_REPOINTS = {"Aring": ("ring", "ringcomb")}

# The hand-written `aalt` block is boilerplate carried over from the wider Noto Sans
# family: 16 of the features it lists do not exist in this font (feaLib warns once for
# each), and `frac` only contributes slash -> fraction, which upstream's own generated
# `aalt` block leaves out. Keep the two that apply.
AALT_FEATURES = ["ccmp", "rtlm"]

# 3./4. Accent centering (Chromium, WebKit) and lowering (WebKit).
#
# The three `*abovecomb` marks have no non-combining code point, so browsers place them
# as standalone accents and get the horizontal position wrong; center them in the advance
# width. And Safari renders <mover accent="true"> as-is, so the empty space an accent
# carries above the baseline becomes a gap between the base letter and its accent; drop
# every accent so its lowest point sits exactly on the baseline.
ACCENTS = [
    "circumflex",           # U+02C6, already drawn by upstream
    "grave",                # U+0060
    "ring",                 # U+02DA
    "rightarrowabovecomb",  # U+20D7 (\vec)
    "threedotsabovecomb",   # U+20DB (\dddot)
    "fourdotsabovecomb",    # U+20DC (\ddddot)
    *NEW_ACCENTS,
]


def bounds(font, glyph):
    """Tight bounding box, with components resolved."""
    return glyph.getBounds(font.layers.defaultLayer)


def single_component(glyph):
    """The (scale, y-offset) of a glyph that is one scaled copy of another glyph."""
    (component,) = glyph.components
    scale, _, _, _, _, dy = component.transformation
    return scale, dy


def enlarge_prime(font, name):
    glyph, ssty1, ssty2 = font[name], font[f"{name}.ssty1"], font[f"{name}.ssty2"]
    scale1, dy1 = single_component(ssty1)
    scale2, dy2 = single_component(ssty2)
    left_sidebearing = bounds(font, glyph)[0]

    for contour in glyph.contours:
        for point in contour.points:
            point.x = otRound(point.x * scale1)
            point.y = otRound(point.y * scale1 + dy1)
    for component in glyph.components:
        # The base glyph was enlarged by an earlier pass, so it already carries the scale
        # and the vertical shift; only the offsets between the copies still need scaling.
        _, _, _, _, dx, dy = component.transformation
        component.transformation = (1, 0, 0, 1, otRound(dx * scale1), dy)

    # Growing the glyph must not move it away from the edge of its advance.
    glyph.move((left_sidebearing - bounds(font, glyph)[0], 0))
    glyph.width = ssty1.width

    # `ssty1` is now the base glyph itself, and `ssty2` has to undo the transform baked
    # into the base before applying its own, so that both keep rendering at the size
    # upstream drew them at.
    ssty1.clearContours()
    ssty1.components = [Component(name, (1, 0, 0, 1, 0, 0))]
    ssty2.clearContours()
    ssty2.components = [
        Component(name, (scale2 / scale1, 0, 0, scale2 / scale1, 0,
                         otRound(dy2 - dy1 * scale2 / scale1)))
    ]


def add_accent(font, name, source, code_point, width):
    glyph = font.newGlyph(name)
    glyph.unicodes = [code_point]
    glyph.width = width
    glyph.components.append(Component(source, (1, 0, 0, 1, 0, 0)))
    font.lib["public.glyphOrder"].append(name)


def center_horizontally(font, name):
    glyph = font[name]
    xmin, _, xmax, _ = bounds(font, glyph)
    glyph.move((otRound(glyph.width / 2 - (xmin + xmax) / 2), 0))


def lower_to_baseline(font, name):
    glyph = font[name]
    glyph.move((0, -bounds(font, glyph)[1]))


def repoint_component(font, name, old_base, new_base):
    found = False
    for component in font[name].components:
        if component.baseGlyph == old_base:
            component.baseGlyph = new_base
            found = True
    if not found:
        raise SystemExit(f"{name} no longer references {old_base}")


def trim_aalt(font):
    body = "".join(f"    feature {tag};\n" for tag in AALT_FEATURES)
    boilerplate = re.compile(r"feature aalt \{\n(?:    feature \w+;\n){3,}\} aalt;")
    text, count = boilerplate.subn(f"feature aalt {{\n{body}}} aalt;", font.features.text)
    if count != 1:
        raise SystemExit(f"expected one boilerplate aalt block, found {count}")
    font.features.text = text


def apply_patches(font):
    for name in PRIME_FAMILIES:
        enlarge_prime(font, name)

    for name, (old_base, new_base) in COMPOSITE_REPOINTS.items():
        repoint_component(font, name, old_base, new_base)

    for name, (source, code_point, width) in NEW_ACCENTS.items():
        add_accent(font, name, source, code_point, width)

    for name in ACCENTS:
        center_horizontally(font, name)
        lower_to_baseline(font, name)

    trim_aalt(font)


if __name__ == "__main__":
    font = Font.open(sys.argv[1])
    apply_patches(font)
    font.save()

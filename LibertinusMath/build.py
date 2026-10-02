"""Build LibertinusMath-Regular.otf straight out of the FontForge source.

Run with a Python that can import FontForge's `fontforge` module (see `build_otf.sh`):

    python build.py <input.sfd> <features.fea> <output.otf>

`<input.sfd>` is a pristine upstream snapshot; `patches.py` applies this project's changes
to the font in memory, first thing after it is opened.

The `.sfd` already carries everything OpenType needs — outlines, GPOS lookups, GDEF
classes and the whole `MATH` table (`MATH:` font entries plus per-glyph
`ItalicCorrection`/`TopAccentHorizontal`/`GlyphVariants*`) — so `font.generate()` writes
it out directly. Apart from the patches, all this script adds is what lives outside the
`.sfd`: the GSUB features from `features/`, the over/underline glyphs, and a refreshed
copyright.

`<features.fea>` is `features/gsub.fea` after `patches.py` has substituted the patched
feature files and the C preprocessor has resolved its `#ifdef MATH` includes;
`build_otf.sh` runs both steps first. What actually gets merged is that file plus the
generated over/underline feature, written out next to the output as `features.fea` so it
can be inspected.
"""

import datetime
import os
import sys

import fontforge

from patches import apply_patches

# Over/underline glyph generation.
#
# U+0305 and U+0332 are zero-width marks that have to stretch to the width of whatever
# they sit on. There is no OpenType mechanism for that, so draw one fixed-width copy per
# width bucket and pick between them with a contextual `mark` substitution.
OVER_UNDER_BASES = ("uni0305", "uni0332")
WIDTH_BUCKET = 50  # glyph advances are rounded to this before grouping


def update_metadata(font):
    year = datetime.date.today().year
    font.copyright = f"Copyright © 2012-{year} The Libertinus Project Authors."


def contour_orientations(font, glyph, xform=(1, 0, 0, 1, 0, 0)):
    """Yield the sign of the transform under which each of `glyph`'s contours ends up.

    A `Refer:` line with a negative determinant (a mirror, e.g. ∤ = a bar plus a flipped
    solidus) reverses the direction of the contours it brings in. Composing the transforms
    down the reference tree tells us which contours arrive reversed.
    """
    a, b, c, d = xform[:4]
    if len(glyph.layers[glyph.activeLayer]):
        yield 1 if a * d - b * c >= 0 else -1
    for name, t, *_ in glyph.references:
        composed = (t[0] * a + t[1] * c, t[0] * b + t[1] * d,
                    t[2] * a + t[3] * c, t[2] * b + t[3] * d, 0, 0)
        yield from contour_orientations(font, font[name], composed)


def refresh_references(font):
    """Rebuild every reference's copy of the glyph it points at, components first.

    A reference carries its own transformed copy of the referenced outline. It is what the
    CFF writer emits for a reference that is more than a shift, what `unlinkRef()` turns
    into contours, and what the composite's bounding box — so its `hmtx` left side bearing —
    is measured on. FontForge's GUI build refreshes those copies whenever a glyph changes;
    the GUI-less one behind the `fontforge` Python module (and Homebrew's `fontforge`) does
    not, so without this, a composite keeps its components as they were before the patches
    moved them and before `round()`.

    Assigning `references` rebuilds them. It also drops `use_my_metrics` and
    `round_translation_to_grid`, which only mean something in a TrueType `glyf` table.
    """
    done = set()

    def refresh(glyph):
        if glyph.glyphname in done:
            return
        done.add(glyph.glyphname)
        references = glyph.references
        for name, *_ in references:
            refresh(font[name])
        if references:
            # The setter prepends, so hand it the list backwards to keep the order.
            glyph.references = tuple(reversed(references))

    for glyph in font.glyphs():
        refresh(glyph)


def fix_mirrored_windings(font):
    """Make contours brought in by a mirrored reference run the same way as the rest.

    Where a glyph mixes mirrored and unmirrored contours, the two windings cancel under
    the non-zero fill rule and the overlap renders as a hole — a notch where the slash of
    ∤ ∦ ∌ crosses the symbol underneath. Unlinking the references turns them into real
    contours (`correctDirection()` ignores references) that `correctDirection()` can then
    reorient. Only glyphs that actually mix are touched: on a glyph whose contours overlap,
    `correctDirection()` can just as easily get the answer wrong.
    """
    for glyph in font.glyphs():
        if len(set(contour_orientations(font, glyph))) > 1:
            glyph.unlinkRef()
            glyph.correctDirection()


def make_over_under_line(font):
    """Draw the width-matched over/underlines and return the `mark` feature that picks them.

    Returns feature-file text, or "" if the font has neither base glyph.
    """
    bases = [n for n in OVER_UNDER_BASES if n in font]
    if not bases:
        return ""

    # Group glyphs by advance width rounded to WIDTH_BUCKET; each group gets one
    # over/underline of that width.
    widths = {}
    for glyph in font.glyphs():
        if glyph.glyphclass != "mark" and glyph.width > 0:
            width = max(round(glyph.width / WIDTH_BUCKET) * WIDTH_BUCKET, WIDTH_BUCKET)
            widths.setdefault(width, []).append(glyph.glyphname)
    if len(widths) == 1:
        return ""

    for name in bases:
        _, ymin, _, ymax = font[name].boundingBox()
        for width in sorted(widths):
            glyph = font.createChar(-1, f"{name}.{width}")
            glyph.width = 0
            glyph.glyphclass = "mark"
            pen = glyph.glyphPen()
            pen.moveTo((-25 - width, ymin))
            pen.lineTo((-25 - width, ymax))
            pen.lineTo((25, ymax))
            pen.lineTo((25, ymin))
            pen.closePath()
            pen = None  # a glyphPen must be released before the glyph is used again

    fea = ["feature mark {",
           f"  @OverSet = [{' '.join(bases)}];",
           "  lookupflag UseMarkFilteringSet @OverSet;"]
    for width in sorted(widths):
        fea.append("  sub [%s] [%s]' by [%s];" % (
            " ".join(widths[width]),
            " ".join(bases),
            " ".join(f"{name}.{width}" for name in bases)))
    fea.append("} mark;")
    return "\n".join(fea) + "\n"


def main():
    sfd, features, output = sys.argv[1:4]
    build_dir = os.path.dirname(output) or "."

    font = fontforge.open(sfd)
    apply_patches(font)
    refresh_references(font)
    update_metadata(font)

    # One `mergeFeature()` call for everything: a feature file merged on its own would
    # only see DFLT/dflt, and the over/underline substitutions have to reach every
    # `languagesystem` that `gsub.fea` declares.
    with open(features) as f:
        combined = f.read() + "\n" + make_over_under_line(font)
    combined_path = os.path.join(build_dir, "features.fea")
    with open(combined_path, "w") as f:
        f.write(combined)
    font.mergeFeature(combined_path)

    fix_mirrored_windings(font)

    # Several `Refer:` offsets in the .sfd are fractional (-88.5, 382.46, …) and FontForge
    # will happily write fractional CFF coordinates. `round()` works on the selection.
    font.selection.all()
    font.round()
    refresh_references(font)

    font.generate(output, flags=("opentype", "no-mac-names", "no-FFTM-table"))


if __name__ == "__main__":
    main()

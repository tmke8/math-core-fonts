"""Drop glyphs that nothing can reach.

Upstream's `.sfd` carries a lot that a math font on the web never uses: 66 German road
sign pictograms inherited from Linux Libertine (`uniE3EB` is "end of pedestrian zone"),
plus alternates such as `Adieresis` and `A.alt` that were stranded when the math `cmap`
was pointed at their `.alt` forms instead. None of them has a code point, a GSUB rule
producing it, or a place in the `MATH` table. Together they are ~7% of the file.

Run over the FontForge output, before hinting:

    python prune.py <input.otf> <output.otf>

This is the step `build.py` used to carry as a commented-out `_prune()`. Reinstating it
verbatim would have been a bug: it seeded the subsetter with `unicodes=` only, and
fontTools prunes `MATH` against the glyphs it was *seeded* with rather than the layout
closure. `integral.sl` and its nine siblings are reachable only through the `ss08`
feature, so their vertical stretch constructions were silently dropped — the slanted
integrals survived but could no longer grow to display size. Seeding with the closed-over
glyph set instead keeps them.
"""

import sys

from fontTools import subset
from fontTools.ttLib import TTFont


def _options():
    options = subset.Options()
    options.set(layout_features="*", name_IDs="*", notdef_outline=True,
                recalc_average_width=True, recalc_bounds=True, glyph_names=True)
    return options


def _math_targets(font):
    """Map each glyph to the glyphs its `MATH` entry pulls in."""
    variants = font["MATH"].table.MathVariants
    targets = {}
    for coverage, constructions in ((variants.VertGlyphCoverage, variants.VertGlyphConstruction),
                                    (variants.HorizGlyphCoverage, variants.HorizGlyphConstruction)):
        if not coverage:
            continue
        for name, construction in zip(coverage.glyphs, constructions):
            reached = [r.VariantGlyph for r in construction.MathGlyphVariantRecord or []]
            if construction.GlyphAssembly:
                reached += [p.glyph for p in construction.GlyphAssembly.PartRecords]
            targets.setdefault(name, []).extend(reached)
    return targets


def reachable(path):
    """Glyphs reachable from the `cmap`, following GSUB and `MATH` to a fixed point.

    fontTools does the GSUB closure — hand-rolling it would miss extension subtables if
    upstream ever starts using them. `MATH` is not part of that closure, so it is applied
    here and the whole thing repeated: a variant reached through `MATH` can itself be the
    input of a GSUB rule (`integral.size1` is a `MATH` variant of `integral` and the `ss08`
    source for `integral.slsize1`), so one pass is not enough.
    """
    targets = _math_targets(TTFont(path))
    keep = None
    while True:
        font = TTFont(path)
        subsetter = subset.Subsetter(options=_options())
        if keep is None:
            subsetter.populate(unicodes=font["cmap"].getBestCmap().keys())
        else:
            subsetter.populate(glyphs=sorted(keep))
        subsetter.subset(font)

        closed = set(font.getGlyphOrder())
        grown = closed.union(*(targets.get(n, []) for n in closed)) if closed else closed
        if grown == keep:
            return keep
        keep = grown


def main():
    source, output = sys.argv[1:3]
    keep = reachable(source)

    font = TTFont(source)
    dropped = len(font.getGlyphOrder()) - len(keep)
    subsetter = subset.Subsetter(options=_options())
    subsetter.populate(glyphs=sorted(keep))
    subsetter.subset(font)
    font.save(output)
    print(f"pruned {dropped} unreachable glyphs, {len(keep)} kept")


if __name__ == "__main__":
    main()

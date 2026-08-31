"""Browser-compatibility patches applied to the pristine upstream NewCMMath-Book.sfd.

The `.sfd` in this directory is an unmodified upstream snapshot; every deviation from
upstream lives here and is re-applied at build time by `build_otf.sh`. See the repo
`README.md` for why each patch is needed.

No patch alters a curve: they copy an existing outline onto another code point,
translate an outline within glyph space, change an advance width, or declare a
variation sequence that resolves to a glyph the font already has.
"""

# 1. Primes always big.
#
# Browsers do not apply the `ssty` feature to primes, so U+2032 & friends render at
# full size where a raised, script-sized prime is wanted. Overwrite each base prime
# with its own `.st` (= ssty1) variant, advance width and hints included.
BIG_PRIMES = [
    "minute",         # U+2032 prime
    "primereversed",  # U+2035 reversed prime
    "uni2033",        # U+2033 double prime
    "uni2036",        # U+2036 reversed double prime
    "uni2034",        # U+2034 triple prime
    "uni2037",        # U+2037 reversed triple prime
    "uni2057",        # U+2057 quadruple prime
]

# 2. Non-combining accents built from the combining ones.
#
# Upstream draws `breve`/`caron` as separate, slightly different outlines from their
# combining counterparts. Use the combining shapes so that an accent looks the same
# whichever code point the browser picks.
ACCENT_SOURCES = {
    # "breve": "brevecmb",
    # "caron": "caroncmb",
}

# 3. Accent centering (Chromium, WebKit).
#
# These three have no non-combining code point, so browsers place them as standalone
# accents and get the horizontal position wrong. Center the outline in the advance width.
CENTERED = [
    "uni0300",  # combining grave accent (\grave)
    "uni0301",  # combining acute accent (\acute)
    "circumflexcmb",  # combining circumflex accent (\hat)
    "uni0304",  # combining macron (\bar)
    "overlinecmb",  # combining overline (\overline)
    "uni0307",  # combining dot above (\dot)
    "uni0308",  # combining diaeresis (\ddot)
    "uni030A",  # combining ring above (\mathring)
    "uni20D7",  # combining right arrow above (\vec)
    "uni20DB",  # combining three dots above (\dddot)
    "uni20DC",  # combining four dots above (\ddddot)
    "brevecmb", # combining breve
    "caroncmb", # combining caron
    "tildecomb", # combining tilde
]

# 4. Accent lowering (WebKit).
#
# Safari renders <mover accent="true"> as-is, so the empty space an accent normally
# carries above the baseline becomes a gap between the base letter and its accent.
# Drop each accent so that its lowest point sits exactly on the baseline. y=0 is the top
# of the font's first blue zone ([-22, 0]), so the bottom edge gets snapped to the pixel
# grid consistently across accents and sizes.
LOWERED = [
    # "grave",       # U+0060
    # "acute",       # U+00B4
    # "circumflex",  # U+02C6
    # "tilde",       # U+02DC
    # "macron",      # U+00AF
    # "breve",       # U+02D8
    # "dotaccent",   # U+02D9
    # "dieresis",    # U+00A8
    # "ring",        # U+02DA
    # "caron",       # U+02C7
    "uni20D7",
    "uni20DB",
    "uni20DC",
    "uni0300",
    "uni0301",
    "circumflexcmb",
    "uni0304",
    "overlinecmb",
    "uni0307",
    "uni0308",
    "uni030A",
    "brevecmb",
    "caroncmb",
    "tildecomb",
]

# 5. Calligraphic variation sequences.
#
# Unicode standardises two variation sequences on each of the 52 script and bold-script
# capitals: <letter, U+FE00> asks for the chancery shape (`\mathcal`), <letter, U+FE01>
# for the roundhand one (`\mathscr`). Upstream declares only the U+FE01 half, on the
# `.alt` glyphs, presumably because this font's default shape is already the chancery
# one and so U+FE00 has nothing to select.
#
# But a font that does not list a sequence does not *support* it, and browsers treat
# that as a reason to go looking for a font that does: Firefox then draws the chancery
# letter from whatever fallback font it lands on, in the wrong design. Declaring the
# sequences with no glyph attached — a "default UVS" record, meaning "supported; use the
# glyph the plain code point already maps to" — is the answer, and it is what FontForge
# writes when the alternate encoding sits on the base glyph itself.
#
# The set is not spelled out here: it is read back off the `.alt` glyphs, so the U+FE00
# half stays in step with whatever upstream declares for U+FE01.
CHANCERY_SELECTOR = 0xFE00   # \mathcal
ROUNDHAND_SELECTOR = 0xFE01  # \mathscr


def copy_outline(font, dest, src, copy_width):
    """Replace `dest`'s outline and hints with `src`'s, optionally its advance width too."""
    font[dest].foreground = font[src].foreground
    font[dest].hhints = font[src].hhints
    font[dest].vhints = font[src].vhints
    if copy_width:
        font[dest].width = font[src].width


def translate(glyph, dx, dy):
    """Move every point of `glyph`, leaving its advance width alone.

    `Glyph.transform` shifts the advance along with the outline, which is not what any
    of these patches want, so put the width back afterwards.
    """
    width = glyph.width
    glyph.transform((1, 0, 0, 1, dx, dy))
    glyph.width = width


def center_horizontally(font, name):
    glyph = font[name]
    xmin, _, xmax, _ = glyph.boundingBox()
    translate(glyph, round(glyph.width / 2 - (xmin + xmax) / 2), 0)


def lower_to_baseline(font, name):
    glyph = font[name]
    _, ymin, _, _ = glyph.boundingBox()
    translate(glyph, 0, -ymin)


def declare_default_variants(font, selector, alongside):
    """Declare <base char, `selector`> for every char that already has <base, `alongside`>.

    The alternate encoding goes on the glyph the plain code point maps to, which is what
    makes it a *default* UVS record rather than a mapping to some other outline.
    """
    by_unicode = {glyph.unicode: glyph for glyph in font.glyphs() if glyph.unicode != -1}
    for code_point in sorted(
        uni
        for glyph in font.glyphs()
        for uni, variation_selector, _ in glyph.altuni or ()
        if variation_selector == alongside
    ):
        glyph = by_unicode[code_point]
        glyph.altuni = (glyph.altuni or ()) + ((code_point, selector, 0),)


def apply_patches(font):
    for name in BIG_PRIMES:
        # The script-sized prime is narrower, so its width comes along.
        copy_outline(font, name, name + ".st", copy_width=True)

    for dest, src in ACCENT_SOURCES.items():
        # Combining marks have zero advance; keep the non-combining width.
        copy_outline(font, dest, src, copy_width=False)

    for name in CENTERED:
        center_horizontally(font, name)

    for name in LOWERED:
        lower_to_baseline(font, name)

    # The moved outlines carry upstream's hints, which are now at the wrong height.
    for name in LOWERED:
        font[name].autoHint()

    declare_default_variants(font, CHANCERY_SELECTOR, alongside=ROUNDHAND_SELECTOR)


if __name__ == "__main__":
    # Debugging aid: `fontforge -lang=py -script patches.py` writes the patched font back
    # out as an .sfd. A FontForge open/save round-trip is byte-identical, so
    #
    #     diff NewCMMath-Book.sfd NewCMMath-Book-patched.sfd
    #
    # shows the effect of the patches and nothing else. The output is gitignored — it is
    # a build artifact, not a source file.
    import fontforge

    font = fontforge.open("NewCMMath-Book.sfd")
    apply_patches(font)
    font.save("NewCMMath-Book-patched.sfd")

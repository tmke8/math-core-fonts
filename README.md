# math-core-fonts

Font source files for math fonts, patched to work better with MathML in browsers. This patching is hopefully only required temporarily while MathML support in browsers is still a bit rough. This is a companion project to [math-core](https://github.com/tmke8/math-core).

The following fonts are included:

- **LibertinusMath** (in `LibertinusMath/`)
- **NewComputerModernMath** (in `NewComputerModernMath/`)
- **NotoSansMath** (in `NotoSansMath/`)

The patches applied to the fonts don't change any glyph shapes. We only rearrange glyphs or change their positioning within glyph space.

## What is patched?

The patching addresses three problems that appear across various browsers.

### 1. Prime symbol replacement

The LaTeX command `\prime` produces a large standard prime symbol as opposed to a raised small symbol. To render this correctly in MathML, we replace the normal prime symbol (which in these fonts is raised and small) with the subscript variant of that same symbol.

Affected code points:

| Code Point | Name |
|---|---|
| U+2032 | Prime |
| U+2033 | Double Prime |
| U+2034 | Triple Prime |
| U+2035 | Reversed Prime |
| U+2036 | Reversed Double Prime |
| U+2037 | Reversed Triple Prime |
| U+2057 | Quadruple Prime |

All browsers are affected by this, as it is fundamentally a font-level issue rather than a browser bug.

LibertinusMath does not need a glyph patch, because upstream already ships an `ssty` feature that performs exactly this substitution — for six of the seven code points above, leaving out U+2057 Quadruple Prime. We do not use that feature for this purpose, though: we want `ssty` free for [its general job of supplying script-size variants](#extending-ssty-in-libertinusmath). So this repository adds `ss09`, which repeats upstream's prime rules and adds the missing U+2057. Enabling `ss09` gives the raised primes for all seven.

A proper solution would be for all math fonts to provide such a feature setting.

### 2. Accent centering

**Affected browsers:** Chromium (Blink), Safari (WebKit)

Three combining diacritical marks used as math accents are not centered correctly:

| Code Point | Name |
|---|---|
| U+20D7 | Combining Right Arrow Above |
| U+20DB | Combining Three Dots Above |
| U+20DC | Combining Four Dots Above |

The root cause is that Unicode doesn't have dedicated code points for these symbols in a non-combining form. Since combining diacritical marks are not meant to appear on their own, Chromium and Safari have trouble handling them as standalone accents.

Upstream draws all three to the left of the origin, as a combining mark should be; we centre them on it instead. Their MATH `TopAccentHorizontal` values and GPOS anchors move along with the outlines, so a renderer that positions accents by the attachment point rather than by the glyph's centre still gets them right.

The proper solution would be for all browsers to handle these correctly.

### 3. Accent lowering

**Affected browsers:** Safari (WebKit)

Safari displays accents in MathML's `<mover accent="true">` element as-is, which results in large wasted space between the accented letter and the accent. What Safari *should* do (and what other browsers do) is display only the accent itself without surrounding white space in the glyph.

To work around this, we patch accent glyphs so that they sit at the bottom of the glyph space, which then produces correct output in Safari.

Affected code points:

| Code Point | Name |
|---|---|
| U+0060 | Grave Accent |
| U+00A8 | Diaeresis |
| U+00AF | Macron |
| U+00B4 | Acute Accent |
| U+02C6 | Modifier Letter Circumflex Accent |
| U+02C7 | Caron |
| U+02D8 | Breve |
| U+02D9 | Dot Above |
| U+02DA | Ring Above |
| U+02DC | Small Tilde |

The proper solution is for Safari to implement the same behavior as the other browsers.

## LibertinusMath-only changes

The three patches above are browser workarounds and apply to all three fonts. LibertinusMath gets three more, which are not browser workarounds: they fix things about the font itself that only show up in math typesetting.

### Extending `ssty`

`ssty` is the OpenType feature a math renderer uses to swap in glyphs drawn for script size. These are proportionally sturdier shapes that look good in superscripts and subscripts. LibertinusMath's sources contain a large set of such `.ssty` glyphs, but upstream's feature file registers only six of them, all primes. Everything else is not reachable.

We register more of them. The feature now covers:

| Registered | Count |
|---|---|
| Primes (as listed above) | 7 |
| Latin lowercase `a`–`z` | 26 |
| Mathematical bold lowercase (U+1D41A–U+1D433) | 26 |
| Mathematical bold digits (U+1D7CE–U+1D7D6) | 9 |
| `+`, `−`, `=`, `(`, `)` | 5 |

Some of the available glyphs are deliberately left unregistered:

- **Sans-serif and sans-serif bold** (U+1D5BA–, U+1D5EE–, and their digits): these carry noticeably more stroke weight than the design calls for at script size, so they look too heavy next to the surrounding text.
- **Plain digits `0`–`9`**: same problem, though a bit less pronounced.
- **Mathematical italic lowercase** (U+1D44E–U+1D467): their shapes differ too much from the non-`ssty` forms.

One additional notes: U+1D7D7 (mathematical bold digit nine) has no `.ssty` glyph in the sources.

### Slanted stretched integrals

Upstream draws the stretched (display-size) integrals upright and keeps the slanted forms — the shape TeX and essentially every other math font uses — behind the `ss08` feature. Browsers don't enable `ss08`, so `\int` grows into an upright integral as soon as it is stretched, which does not match the unstretched glyph.

We copy each slanted variant over its upright counterpart, so the stretched integral is slanted out of the box. `ss08` keeps working; it now substitutes glyphs identical to its inputs.

While moving them, we also re-centre the family vertically. Upstream centres the stretched integrals on the middle of the ascender–descender span, which leaves them sitting visibly high against the fraction bars and relation symbols they are set with; they are now centred on the font's `AxisHeight`, which is what a math renderer aligns to.

Affected code points: U+222B–U+2233 (the integral signs, single through anticlockwise contour) and U+2A0C Quadruple Integral, in their stretched forms only.

### Ratio spacing

U+2236 Ratio is drawn as two stacked periods, but upstream gives it an advance width of 527 units — more than twice that of `:` — so `a ∶ b` comes out with a conspicuous gap on either side of the symbol. We give it the same advance width and left side bearing as `:`. The dots themselves are not moved.

## NewComputerModernMath-only changes

### Calligraphic variation sequences

`\mathcal` and `\mathscr` share the same Unicode code points, and the two shapes are told apart by a following variation selector: `<letter, U+FE00>` selects the chancery (`\mathcal`) form, `<letter, U+FE01>` the roundhand (`\mathscr`) one. The sequences are standardised for the 52 script and bold-script capitals (U+1D49C–U+1D4B5 and U+1D4D0–U+1D4E9, with the eight letterlike ones ℬ ℰ ℱ ℋ ℐ ℒ ℳ ℛ standing in for the holes in the first range).

NewComputerModernMath draws chancery by default and ships the roundhand outlines as `.alt` glyphs, but upstream declares only the U+FE01 half of each pair: U+FE00 has no separate glyph to point at, and leaving it out may look harmless because the base glyph is already the shape being asked for. But it is not harmless: A sequence a font does not list is a sequence the font does not *support*, and browsers use that to pick a font — Firefox goes looking for one that does declare it, and 𝒜︀ comes back drawn in a fallback font rather than in NewCM.

The fix costs no glyphs: the code points are given a second, U+FE00-tagged encoding on the glyph they already map to, which the `cmap` format 14 subtable records as a *default* UVS entry — "this sequence is supported; use the ordinary glyph". U+FE01 keeps pointing at the `.alt` outlines as before.

The set of letters is read back out of the font's existing U+FE01 entries rather than listed in the patch, so the two halves cannot drift apart when upstream changes.

## Building

Each font requires different tooling, but they all follow the same general pattern: a bash script produces an OpenType (`.otf`) file, which can then be compressed to `.woff2` for use in the browser.

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [FontForge](https://fontforge.org) (needed for LibertinusMath and NewComputerModernMath)
- [woff2](https://github.com/google/woff2) (for `woff2_compress`)

### Steps

1. Install Python dependencies:
   ```sh
   uv sync
   ```

2. `cd` into the font directory, e.g.:
   ```sh
   cd NotoSansMath
   ```

3. Run the build script:
   ```sh
   bash build_otf.sh
   ```

4. Compress the resulting OTF to WOFF2:
   ```sh
   woff2_compress <FontName>.otf
   ```

## License

- **LibertinusMath** and **NotoSansMath** are released under the [SIL Open Font License](https://openfontlicense.org). See the `OFL.txt` file in their respective directories.
- **NewComputerModernMath** is released under the [GUST Font License](https://www.gust.org.pl/projects/e-foundry/licenses). See `GUST-FONT-LICENSE.txt` in its directory.

As noted above, we do not modify any glyph shapes.

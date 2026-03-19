# math-core-fonts

Font source files for math fonts, patched to work better with MathML in browsers. This patching is hopefully only required temporarily while MathML support in browsers is still a bit rough. This is a companion project to [math-core](https://github.com/tmke8/math-core).

The following fonts are included:

- **LibertinusMath** (in `LibertinusMath/`)
- **NewComputerModernMath** (in `NewComputerModernMath/`)
- **NotoSansMath** (in `NotoSansMath/`)

The patches applied to the fonts don't change any glyph shapes. We only rearrange glyphs or change their positioning within glyph space.

## What is patched?

The patching addresses three problems that appear across various browsers.

### 1. Prime symbol replacement (`ssty` variant)

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

All browsers are affected by this, as it is fundamentally a font-level issue rather than a browser bug. LibertinusMath already provides a font feature setting for this (`ss08`), so it does not require patching in this regard.

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

## Building

Each font requires different tooling, but they all follow the same general pattern: a bash script produces an OpenType (`.otf`) file, which can then be compressed to `.woff2` for use in the browser.

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [FontForge](https://fontforge.org) (needed for NewComputerModernMath)
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

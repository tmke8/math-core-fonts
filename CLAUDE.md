# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Vendored upstream sources for three OpenType math fonts, patched so that MathML renders
correctly in browsers. Companion to [math-core](https://github.com/tmke8/math-core).
See `README.md` for the full rationale of each patch (prime `ssty` replacement, accent
centering for Chromium/WebKit, accent lowering for WebKit).

**Hard constraint: no glyph shape changes.** Patches only rearrange glyphs (swap which
outline sits at which code point), change advance widths, or translate outlines within
glyph space. If a change would alter a curve, it is out of scope.

Each font directory is a snapshot of a different upstream project with its own source
format, own build tooling, and own license — there is no shared build system, and the
per-font `README.md`/`OFL.txt`/`AUTHORS.txt` files are upstream's, not this project's.

All three follow the same rule: the vendored sources are untouched, and every deviation
from upstream lives in that directory's `patches.py`, applied at build time. Re-vendoring
an upstream release is a plain file replacement, and the patches show up in `git log` as
readable diffs instead of raw coordinates.

## Fonts, source formats, and builds

| Directory | Source | Build tooling |
|---|---|---|
| `LibertinusMath/` | `LibertinusMath-Regular.sfd` + `features/*.fea` (both **pristine upstream**) + `patches.py` + `features/*.fea.new` | `fontforge` binary + gftools |
| `NewComputerModernMath/` | `NewCMMath-Book.sfd` (FontForge, **pristine upstream**) + `patches.py` | `fontforge` binary only |
| `NotoSansMath/` | `NotoSansMath-Regular.ufo/` (**pristine upstream**) + `patches.py` | `fontmake` |

Prerequisites: `uv`, FontForge (Libertinus and NewCM), `woff2` (for `woff2_compress`).

```sh
uv sync                                   # once, at repo root

cd NotoSansMath && uv run bash build_otf.sh          # or LibertinusMath
woff2_compress NotoSansMath-Regular.otf

cd NewComputerModernMath && bash build_otf.sh        # no uv — uses system fontforge
woff2_compress NewCMMath-Book.otf
```

`.otf` and `.woff2` outputs plus `LibertinusMath/build/` and `NotoSansMath/build/`
are gitignored. There is no test
suite and no linter; verification is visual/rendering-based.

`.github/workflows/build-and-deploy.yml` builds all three in parallel jobs, uploads
`.otf` + `.woff2` artifacts, and on pushes to `main` deploys them to GitHub Pages.

### NewComputerModernMath build pipeline

`NewCMMath-Book.sfd` is an **unmodified upstream snapshot — never edit it**. Every
deviation from upstream lives in `patches.py`, which `build_otf.sh` applies to the
in-memory FontForge font between `fontforge.open()` and `font.generate()`. Re-vendoring
upstream is therefore a plain file replacement, and the patches show up in `git log` as
readable diffs instead of raw `SplineSet` coordinates.

`patches.py` is declarative: four tables (`BIG_PRIMES`, `ACCENT_SOURCES`, `CENTERED`,
`LOWERED`) name glyphs, and `apply_patches()` runs copy-outline / center / lower over
them, then `autoHint()`s everything it moved (equivalent to Hints > AutoHint in the GUI —
verified to produce byte-identical CFF hint operators). Note that FontForge's
`Glyph.transform` shifts the advance width along with the outline, so the local
`translate()` helper restores it.

For debugging, `fontforge -lang=py -script patches.py` (from inside the directory) writes
the patched font back out as `NewCMMath-Book-patched.sfd` (gitignored). A FontForge
open/save round-trip is byte-identical to the input, so `diff NewCMMath-Book.sfd
NewCMMath-Book-patched.sfd` shows the patches and nothing else — apart from
`ModificationTime` and a `VWidth:` line FontForge adds to each touched glyph, which does
not reach the `.otf` (the build emits no `vhea`/`vmtx`).

The operations are relative to each glyph's own bounding box (center in the advance
width; drop the lowest point onto the baseline), so they stay correct if upstream
redraws or repositions an accent. After an upstream update the thing to watch for is
`patches.py` failing on a renamed or missing glyph.

### NotoSansMath build pipeline

`NotoSansMath-Regular.ufo/` is an **unmodified upstream snapshot — never edit it**. Every
deviation from upstream lives in `patches.py`; `build_otf.sh` copies the UFO to
`build/`, runs `patches.py` over the copy, and points fontmake at that. So the patched
UFO is always there to inspect: `diff -r NotoSansMath-Regular.ufo build/NotoSansMath-Regular.ufo`.

`patches.py` is declarative — `PRIME_FAMILIES`, `NEW_ACCENTS`, `ACCENTS`,
`COMPOSITE_REPOINTS`, `AALT_FEATURES` — and every geometric operation is relative to the
glyph's own bounding box or to a transform read out of the UFO, so no hand-measured
coordinates appear. Things worth knowing:

- `glyph.move()` moves anchors along with the outline, which is what you want: an accent's
  `math.ta` anchor becomes the MATH `TopAccentAttachment`, and its `_top` anchor drives
  GPOS mark attachment. Editing `.glif` coordinates by hand leaves the anchors behind and
  silently breaks both.
- `Aring` is a composite of `A` + `ring`, so patching `ring` would drag the ring down onto
  the A; `COMPOSITE_REPOINTS` sends Å to the identical `ringcomb` instead. Check for new
  composite users after an upstream update.
- The prime patch reads each family's `.ssty1` transform out of the UFO and bakes it into
  the base glyph, then re-points `.ssty1`/`.ssty2` at the enlarged base. It applies to
  `quadrupleprime` too, which is a composite of four `prime` components.
- Adding a glyph is `font.newGlyph()` plus an append to `public.glyphOrder`; ufoLib2
  writes `contents.plist` and the escaped `.glif` filename on save.

### LibertinusMath build pipeline

`build_otf.sh` chains several stages, each writing into `build/`:

1. `patches.patch_features()` copies `features/` to `build/features/`, replacing
   `ssty.fea` with `ss09.fea.new` + `ssty.fea.new` (see below)
2. `pcpp -D MATH -I build/features` resolves `gsub.fea`'s `#ifdef`s into `build/gsub.fea`
3. `build.py` under `fontforge -lang=py -script` — opens the `.sfd`, runs
   `patches.apply_patches()` over it, generates the over/underline glyphs, appends their
   `mark` feature to `build/gsub.fea` (one combined `build/features.fea`, because a feature
   file merged on its own only reaches DFLT/dflt), merges it, and calls `font.generate()`
4. `prune.py` drops the 240 glyphs nothing can reach (see below)
5. `psautohint` → `cffsubr` → `gftools fix-font` → `font-v` stamps the version

`LibertinusMath-Regular.sfd` and `features/` are **unmodified upstream snapshots — never
edit them**. Every deviation from upstream lives in `patches.py`, in two halves, because
the feature files are consumed by `pcpp` (project venv) and the `.sfd` by FontForge (its
own embedded Python, which cannot see the venv):

- `apply_patches(font)` runs inside `build.py`, first thing after `fontforge.open()`. It is
  declarative — five tables (`SLANTED_INTEGRALS`, `AXIS_CENTRED_INTEGRALS`,
  `RATIO_METRICS_FROM`, `CENTERED`, `LOWERED`) name glyphs, and copy-glyph / translate runs
  over them. Every operation is relative to the glyph's own bounding box or to another
  glyph's metrics, so no coordinate appears in the file and nothing has to be re-measured
  if upstream redraws or repositions something. It must run before `mergeFeature()`,
  because `make_over_under_line()` buckets glyphs by advance width and the patches change
  several widths.
- `patch_features(src, dst)` is plain Python (standard library only, so both interpreters
  can import this module) and is called from `build_otf.sh` before `pcpp`.

Things worth knowing when adding an operation:

- `Glyph.transform` moves the glyph's anchor points but **not** its MATH
  `TopAccentHorizontal`, which is the point a renderer lines an accent up over its base.
  Upstream keeps that value on the midpoint of the outline; `centre_horizontally()` puts it
  back there after the move. Leaving it behind is what the hand-patched `.sfd` did, and it
  shipped `\vec`, `\dddot` and `\ddddot` with attachment points 210, 374 and −378 units
  away from their (centred) ink.
- `transform` also moves the offsets of the glyph's references, which is wrong when the
  referenced glyphs are being moved by the same amount — hence `translate()`'s
  `move_references` argument, used by the integral shift.
- A bounding box read off a glyph in a family that references itself (the integrals) has to
  come from `glyph.foreground`, not `glyph.boundingBox()`, or a reference to an
  already-moved sibling drags the answer.
- **Do not call `Glyph.autoHint()`, and do not touch `Glyph.manualHints`.** Unlike NewCM's,
  this `.sfd` carries no hints at all — not one `HStem:`/`VStem:` line in 4379 glyphs — and
  `psautohint` does the hinting downstream. Upstream's `manualhints` flag (set on 3874 of
  them) is how it keeps FontForge's generate-time autohinter off the glyphs it wants
  `psautohint` to handle; clearing it, or autohinting by hand, just puts hints into
  `build/…-instance.otf` for `psautohint` to throw away again.

The two GSUB changes that cannot sensibly be written as Python stay as feature files:
`features/ss09.fea.new` (the prime feature this repo adds) and `features/ssty.fea.new`
(upstream's `ssty` extended). `patch_features()` concatenates them over the copy of
`ssty.fea` in `build/features/`, which is where `gsub.fea` `#include`s it under
`#ifdef MATH`.

For debugging, `fontforge -lang=py -script patches.py` (from inside the directory) writes
the patched font out as `LibertinusMath-Regular-patched.sfd` (gitignored). Unlike NewCM,
a FontForge open/save round-trip of this `.sfd` is not byte-identical — upstream's file
came out of an older FontForge — so `diff LibertinusMath-Regular.sfd
LibertinusMath-Regular-patched.sfd` also shows `ModificationTime`,
`DisplaySize`/`AntiAlias`/`FitToEm`, a trailing space on every `MATH:` entry that can carry
a device table, and a `VWidth:` line per touched glyph. None of it reaches the `.otf`.

Two more things the diff shows that are FontForge bookkeeping rather than patches: point
*types* get recategorised (`m 0` → `m 2`, curve → tangent) on the glyphs whose outline is
replaced wholesale, and `Glyph.transform` snaps coordinates to 1/1024 (`866.72` becomes
`866.719726562`). Neither survives `font.round()` and the CFF.

`build.py` is short because FontForge already knows the `.sfd` natively: outlines, GPOS
lookups, GDEF classes and the whole `MATH` table (the `MATH:` font entries plus per-glyph
`ItalicCorrection`/`TopAccentHorizontal`/`IsExtendedShape`/`GlyphVariants*`/`GlyphComposition*`)
come out of `font.generate()` with no help. It replaced an inherited-from-upstream script
that went `.sfd` → `sfdLib` → `ufoLib2` → `ufo2ft` and hand-assembled `MATH` with
`fontTools.otTables` — ~200 lines that are now one method call.

Two things the FontForge route needs that the ufo2ft one got for free:

- **`fix_mirrored_windings()`.** A `Refer:` line with a negative determinant (`0 1 1 0`,
  `-1 0 0 1`, …) reverses the contours it pulls in. Where a glyph mixes mirrored and
  unmirrored contours — ∤ ∦ ∌, a flipped solidus over an upright symbol — the windings
  cancel under the non-zero fill rule and the crossing renders as a notch. ufo2ft's
  `removeOverlaps` used to paper over this. The fix walks the reference tree, composes the
  transforms, and runs `unlinkRef()` + `correctDirection()` on the glyphs that mix — and
  *only* those, since `correctDirection()` misjudges glyphs with overlapping contours
  (it hollows out ⨁ if let loose on the whole font).
- **`font.round()`.** Several `Refer:` offsets are fractional (`-88.5`, `382.46`), and
  FontForge happily writes fractional CFF coordinates where ufo2ft rounded. It does not
  reach coordinates produced by decomposing a reference at generate time — ~250 glyphs
  still leave `build/…-instance.otf` fractional — but `psautohint` rounds those, so the
  shipped `.otf` has no fractional coordinates.

Hinting is `psautohint`'s job, but FontForge still hints on the way there: 413 glyphs come
out of `font.generate()` with stem hints, being the ones where upstream did not set
`manualhints` (`bar.size*`, the Fraktur and double-struck alphabets, the `.sl`/`.slsize1`
integrals, plus the over/underlines `build.py` draws itself). `psautohint` overwrites all
of it, so the shipped font is unaffected and this is only untidiness in the intermediate.

**Do not "fix" it by passing `no-hints` to `font.generate()`.** It works — 0 hinted glyphs,
and the Private dict entries `psautohint` reads (blue zones, `StdHW`/`StdVW`, `StemSnap*`)
survive intact — but it takes `BlueShift` down with it. Upstream's Private dict does not
declare a value, so FontForge derives one from the hints it generated; suppress them and it
writes 0, which switches off overshoot suppression at small sizes. `psautohint` passes the
value straight through, so it reaches the shipped font and nothing downstream catches it.
Recovering the current output means pinning `font.private["BlueShift"]` by hand, which is a
worse thing to own than the untidy intermediate.

Overlaps are *not* removed (FontForge's `removeOverlap()` is riskier than pathops and this
font has degenerate contours it errors on). The consequence is that `psautohint` reports
duplicate-subpath/loop errors on 5 glyphs — `uni27F2`, `uni29F7`, `u1D62E`, `uniE3E8`,
`uniE3EB`. All five are zero-area specks and retracing hairlines in upstream's own
outlines that pathops used to delete; psautohint complains but still hints them, and the
shipped font hints all 4434 glyphs that have an outline, exactly as before (the 27
unhinted ones are `space` and the U+2000–U+202F blanks). Slightly different outlines do
mean psautohint derives a different number of stems for 112 glyphs.

### Pruning unreachable glyphs

`prune.py` runs between `build.py` and `psautohint` and drops 240 of 4461 glyphs — with no
change to shaping, `cmap` or `MATH` for anything that survives. What goes:

- 108 `.ssty` variants. 26 are the italic math lowercase (`u1D44E.ssty`…, plus
  `uni210E.ssty`), which no rule has ever reached — no version of `ssty` ever listed them.
  The other 82 were deliberately left out of `ssty.fea.new`: measured against the base
  glyphs, the sans and sans-bold alphabets carry 12–14% more stroke weight than parity at
  `ScriptPercentScaleDown` (80%), so they render visibly heavy at script size. The plain
  digits went with them by eye. Note U+1D7D7 (bold nine) has no `.ssty` glyph drawn at all,
  which is why `ssty.fea.new`'s bold digits stop at `u1D7D6`.
- 66 German road sign pictograms (`uniE3EB` is "end of pedestrian zone"), inherited from
  Linux Libertine. They are not even PUA-*encoded* here — `Encoding: 1114244 -1 2468`, the
  `-1` meaning no code point — so the `uniE####` names are fossils of a mapping that no
  longer exists. Two of them are why `psautohint` used to report errors on `uniE3E8` and
  `uniE3EB`.
- 65 alternates stranded when the math `cmap` was pointed at their `.alt` forms
  (`Adieresis`, `A.alt`, `Q_u`, …), plus `uni0330.size5`, which upstream's `uni0330`
  horizontal variant list never references — it lists `.size3` twice instead.

Do not drop `ssty.fea.new` to shed the rest: it still has to carry the seven prime rules,
and `ss09.fea.new` next to it is the feature the prime patch depends on (`README.md`
describes it — `ss08` is the slanted integrals). Upstream's `features/ssty.fea`, which
these two replace at build time, is 6 prime rules and omits U+2057.

`build.py` used to carry this as a commented-out `_prune()`. **Do not reinstate that
version**: it seeded the subsetter with `unicodes=` only, and fontTools prunes `MATH`
against the seeded set rather than the layout closure, so the ten `.sl` slanted integrals
— reachable only through `ss08` — kept their glyphs but lost their vertical stretch
constructions and could no longer grow. `prune.py` seeds with the closed-over glyph set
instead. The closure has to iterate, because a glyph reached through `MATH` can itself be
a GSUB input (`integral.size1` is a `MATH` variant of `integral` and the `ss08` source for
`integral.slsize1`), and it delegates the GSUB half to fontTools so that extension
subtables keep working if upstream starts using them.

The `features/` directory is a partial copy of upstream Libertinus features (plus this
repo's two `.fea.new` files); `gsub.fea` `#include`s siblings, and several upstream
includes are skipped under `#ifdef MATH`. `build.py` does not preprocess it itself:
FontForge's embedded Python cannot import `pcpp` from the project venv, so `build_otf.sh`
runs `pcpp` as a separate step. For the same reason `build.py` and `patches.py` may only
import the standard library and `fontforge`.

## Editing conventions

- Commit subjects are prefixed with the font: `[Libertinus]`, `[NewCM]`, `[Noto]`, `[All]`.
- Patching NewCM means adding a glyph name to a table in `patches.py` (or a new operation
  next to `center_horizontally`/`lower_to`) — not touching the `.sfd`.
- Patching Libertinus means adding a glyph name to a table in `LibertinusMath/patches.py`,
  or a rule to `features/ssty.fea.new`/`ss09.fea.new` — not touching the `.sfd` or the
  upstream `.fea` files.
- Patching Noto means adding a glyph name to a table in `NotoSansMath/patches.py` — not
  editing `NotoSansMath-Regular.ufo/glyphs/*.glif`.
- Prime handling differs per font by design: Libertinus already ships the raised `.ssty1`
  outlines, so its patch is a feature (`features/ss09.fea.new`) rather than a glyph swap;
  NewCM and Noto have the base prime glyphs overwritten with their small raised variants,
  both via their `patches.py`.

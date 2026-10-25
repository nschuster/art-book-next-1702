# Native achievement trophy candidate — not published

Baseline recovered before edits: `ed3cc5e`, no tracked modifications. Existing unrelated untracked preview directories were left alone. No commit/push or device deployment.

## Exact native source

Batocera 42 ES pin: `4adf26b43900d1a33887af6d8af3da2e99e398a5`.

- `es-app/src/views/gamelist/GameNameFormatter.cpp:16`: `CHEEVOSICON` = `_U("\uF091")`.
- Lines 213–214 append `CHEEVOSICON` after game names when `mShowCheevosIcon && fd->hasCheevos()`.
- `es-core/src/resources/Font.cpp:274–292` registers `:/fontawesome-webfont.ttf` first in fallback order; `getFaceForChar` selects it for missing glyphs.
- ThemeData.cpp PATH handling accepts existing embedded resources (1787–1796).
- Runtime uses U+F091 with that explicit embedded resource, not U+1F3C6 emoji. Static renderer uses the byte-identical pinned font; [font hash, links, copyright/license](../../tools/assets/README.md).

## Latest spacing correction

The previous bar was already aligned to the metadata value slots, but the trophy ink ends 1px inside its slot at both preview resolutions. The user-approved glyph/size is unchanged. Apply an optical correction only: bar x `.5890625`, width `.3609375`, count center x `.76953125`; right edge `.95`, y, height and all typography remain unchanged.

| Framebuffer | Metadata left-column icon x / right; value slot x | Trophy ink right | Bar x before → after | Slot gap before → after | Visible gap before → after | Bar width before → after |
| --- | --- | --- | --- | --- | --- | --- |
| 640×480 | 352 / 372; 378 | 371 | 378 → 377 | 6 → 5 | 7 → **6** | 230 → 231 |
| 320×240 | 176 / 186; 189 | 185 | 189 → 188 | 3 → 2 | 4 → **3** | 115 → 116 |

Bounds use exclusive right edges. The left-column Last Played, playtime and genre visible gaps are 6px/3px. Release-date sample text has a 1px leading bearing at 480p (7px visible gap), and 3px at 240p. Right-column icon raster x is 499/250, right 519/260, value slot x 525/262, sample text ink x 526/262 (visible gap 7/2). Thus metadata has glyph/rounding variation; this correction matches the dominant left-column visible gap rather than claiming every silhouette is identical. The bar is now 1 raster pixel left of the value slots, intentionally compensating for the trophy's inset ink. At 240p normalized bar x is 188.5 and width 115.5 before renderer rounding, so exact native rasterization still requires device QA.

TDD: both new visible-gap regressions failed before the fix (7 != 6 and 4 != 3). Final full suite: **110 passed, 104 subtests passed**; whitespace diff check clean. Regenerated all eight palettes at both resolutions and visually inspected both C64 frames and both contact sheets. `spacing-evidence.json` proves every pixel outside the bar/count region is unchanged in all 16 frames, including trophy, metadata, media and footer. Existing low-alpha contrast limitations remain unchanged. No native device, commit, push or deployment.

## Prior geometry (superseded only by spacing correction above)

At 640×480: trophy box **[352,391,20,22]**, 6px gap, track/fill **[378,391,230,22]**. At 320×240: trophy box **[176,196,10,11]**, 3px gap, bar **[189,196,115,11]**. Combined normalized panel remains x=.55–.95. Original y=.815 and height=.045833333333333 remain unchanged; count center shifts to x=.7703125 in the shortened bar. Count font/size/sidebar color, rainbow and track sources are unchanged. Trophy uses the existing metadata-icon palette binding, no background or badge.

Only generated extras gain the trophy; existing opt-in loader/gating and asset ownership remain unchanged. No runtime theme XML, media assets, metadata layout or palette definitions changed. RA Off therefore retains its existing layout. Upgrade requires reinstalling the helper and regenerating existing XML; private template position overrides must be cleared to use the new center. No fresh credential/configuration prompt is needed.

## Metadata-size correction (latest review)

Only trophy `fontSize` changes from `.027777777777777` to `.03125`; count typography and all component positions/sizes remain unchanged. Measured the actual resolved SVG assets and the exact U+F091 font ink, not nominal point sizes. The existing renderer produces:

| Framebuffer | Metadata image size | Metadata ink (width × height) | Trophy ink before → after | Final trophy ink bounds (exclusive right/bottom) |
| --- | --- | --- | --- | --- |
| 640×480 | 20×20 | 20×20 date/players/clock/playcount; 20×16 last-played; 20×18 genre | 16×16 → **18×16** | [353,394,371,410] |
| 320×240 | 10×10 | 10×10 except players 10×9 | 9×9 → **9×9**, now vertically centered | [176,197,185,206] |

This matches the metadata visual scale within 10% width and the observed silhouette-height envelope (1px rounding allowance), **not identical ink rectangles**. Native font scaling is quantized; enlarging to the next available preview font step at 240p exceeds the 10px slot and would truncate the glyph. Retain the native glyph rather than stretching it or altering the approved gap/bar. The 480p font raster is 19px; 240p is 10px. Trophy ink is centered vertically in the unchanged bar-height box; 6px/3px component gaps and count centering remain unchanged.

TDD correction RED: eight exact-size assertions plus both new raster regressions failed (480p undersize, 240p vertical ink alignment). GREEN: **108 passed, 104 subtests passed**. All eight palettes regenerated at both resolutions with the existing renderer; before/after pixel comparisons are identical everywhere outside the trophy box. `icon-size-evidence.json` records resolved metadata bounds and actual trophy ink. Both C64 frames visually inspected. No native device is available; this remains static Pillow/CairoSVG evidence, not native font-rendering proof.

## Original implementation checks

- TDD RED: 9 new cases failed for absent trophy and missing exact-font preview asset; separate isolation regression failed before replacing the renderer's old default fixture directory with TemporaryDirectory.
- GREEN/full suite: `python -m pytest -q` → **106 passed, 104 subtests passed**.
- `git -c core.whitespace=cr-at-eol diff --check` → clean.
- Tests include zero total, zero/partial/full progress, both count modes, pinned font checksum, all eight palette bindings, both resolutions, overlap/center/fit, and prior mapping/auth/install/lifecycle/layout coverage. Updated only superseded exact bar/count coordinates in existing regressions.
- Generated all eight palette previews at 640×480 and 320×240 in a new directory; historical galleries were not overwritten. Default test renders now use temporary fixture directories.

## Inspected previews

`previews/retroachievements-native-trophy/`:

- **Primary:** `commodore-64-480.png` (640×480).
- **Secondary:** `commodore-64-240.png` (320×240).
- `commodore-64-480-labeled.png` includes external sample/static notice.
- `contact-sheet-1.png`, `contact-sheet-2.png`, `manifest.json`; all eight palettes and both sizes.

Both primary and secondary C64 frames were opened and visually inspected: recognizable small trophy immediately left of the bar, clear positive gap, centered 12/40, no clipping/overlap, original metadata/media present. These are **static sample renders**, not native screenshots or user account results. The small 240p icon/text and existing low-alpha palette/count contrast remain physical-device QA concerns. Native font baseline/antialiasing, live refresh/API and Commodore 1702 overscan/readability were not tested; no native device is available.

# Metadata trophy size match — candidate, not published

The renewed correction is implemented only for generated `ra_progress_trophy`.
No game-list font, global font size, native formatter, theme XML, metadata layout,
palette, or approved OLED contrast source was changed in this task.

## Why an exact outline instead of another font size

Probed the actual pinned U+F091 font with the preview's native-size approximation:
`.03125`, `.032`, and `.033333333333333` all remain 18×16 / 9×9 ink.
`.034` and `.035` produce 19×17 at 480p but 11×10 at 240p, exceeding the
10px slot. `.036` produces 21×19 / 11×10. Increasing a global or count font was
not considered. This quantization cannot match both metadata widths cleanly.

`sync.py:trophy_asset` instead emits the **exact original FontAwesome 4.3.0
U+F091 outline**, extracted with FontTools SVGPathPen from the byte-verified
Batocera 42 font. The extraction is compared byte-for-byte by `verify.py`.
The glyph bounds `(0,-128,1664,1408)` are translated/flipped into a square
1664-unit canvas with uniform scale, retaining handles, bowl, stem and base.
No redrawing, alternate symbol, distortion, clipping or installed font change.
Source copyright Dave Gandy 2015 and SIL OFL 1.1 provenance accompany the SVG;
full source-font license is `tools/assets/OFL-1.1.txt`. The glyph output is a
document under the OFL output exception. No FontTools dependency on Batocera.

## Measured size and preservation

| Framebuffer | Before ink | After alpha ink | After >=50% alpha ink | Image bounds x,y,w,h | Visible gap | Unchanged bar x,y,w,h |
|---|---|---|---|---|---|---|
| 640×480 | 18×16 | **20×20** | 20×18 | 351,392,20,20 | **6px** | 377,391,231,22 |
| 320×240 | 9×9 | **10×10** | 10×10 | 175,196,10,10 | **3px** | 188,196,116,11 |

Metadata SVGs have widths up to 20/10px and varying silhouette heights.
Trophy width now matches exactly, rather than the previous 90% near-match.
At 480p the weak antialiased top/bottom rows account for the difference between
20×20 full alpha bounds and 20×18 >=50% bounds; do not call it a solid 20px-tall
rectangle. The vector aspect is still the original 1664:1536, not square-stretched.

Only trophy `pos`/image size changes: x=.548 (slightly left to retain the approved
optical gap), center y=.837916666666667, size=.03125 .041666666666667.
The square raster rounds to x351/175; normalized fractional native rounding still
needs device confirmation. The count center/font, track/rainbow x/y/width/height
and right edge (608/304) are identical. Generated XML excluding this one extra
is byte-identical to task entry. Four C64/OLED before/after frames have **zero
changed pixels outside the trophy**. Entry-file hashes verify all fonts, theme.xml,
progress-colors.xml and every other runtime source except sync.py stayed unchanged.
The fixture game list does not show native achievement marks, so pixel evidence
alone is not offered as proof of their rendering; source isolation establishes
that the actual game-list path was not touched.

## Native evidence and tests

Pinned Batocera ES `4adf26b43900d1a33887af6d8af3da2e99e398a5`:
ThemeData.cpp image schema lines 114–157 supports every emitted property;
image extra factory at 2197 creates ImageComponent, and DetailedContainer.cpp:532
loads per-game extras. This uses the same supported image/absolute-path mechanism
as the existing progress assets. The trophy shares checksum ownership journaling,
reference tracking and safe collection, including edited/unrelated-asset retention.

Compiled `native-raster.cpp` against the pinned NanoSVG headers, freshly compared
byte-for-byte with upstream. Its **actual rasterized alpha bounds also measure
20×20 / 10×10**, >=50% alpha 20×18 / 10×10, matching the static SVG measurements.
See `native-raster-evidence.json` for header hashes. This validates glyph SVG
rasterization, not the full ES component compositor or physical CRT.

TDD: witnessed 14 failing trophy regressions before implementation. Updated only
the obsolete two-assets expectations and the trophy-specific height exception.
Final full suite: **114 passed, 104 subtests passed**. `git -c
core.whitespace=cr-at-eol diff --check` clean. Lifecycle subprocess tests verify
all three assets actually exist and old fill assets do not accumulate.

## Preview artifacts and upgrade

Directory: `previews/retroachievements-trophy-size-match/`.

- `commodore-64-480-comparison.png` — primary side-by-side.
- `oled-480-comparison.png` — OLED primary side-by-side.
- `commodore-64-240-comparison.png`, `oled-240-comparison.png` — secondary.
- `{scheme}-{480|240}-{before|after}.png` — raw framebuffer images.
- `{scheme}-{480|240}-detail-4x.png` — nearest-neighbor trophy/bar inspection.
- `evidence.json`, `native-raster-evidence.json`, `verify.py`, source snapshots.

Inspected the primary C64 comparison and secondary OLED comparison: larger trophy
retains its native shape, positive gap and original full composition. C64 metadata
is readable; OLED remains intentionally low-alpha outside the previously approved
empty-star/track adjustment. These are static fictional 12/40 samples, not device
captures or account results. Real ES positioning, refresh and Commodore 1702
readability remain unverified. No commit/push/device deployment.

After approval, update/reinstall the helper and regenerate the desired existing
extras (cached counts are sufficient); reselect/reload if necessary. No new user
configuration, credentials, global fonts or native frontend modifications needed.

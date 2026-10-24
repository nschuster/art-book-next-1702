# 4:3 original-media / icon-metadata candidate

The preview-approved layout preserves original media geometry and uses icon-based metadata.

## Layout contract

The layout change is confined to `aspect-ratio-4-3.xml`. The optional Commodore palette additionally changes colors and supplies a palette-only textlist selector in `colors.xml` / `theme.xml`. Manual and dispatched automatic 4:3 Detailed mode, metadata `on|mixed|play-stats`, help on/off: replace description with seven fields. Developer/publisher and all text labels are hidden. Retain release date, rating, players, play count, play time, last played and genre.

The image, video and marquee components are identical to upstream baseline `9a50ef366e750aabfab29e6915a2867607212971`, including sizing, positions, origin, crop and effects. Game list, logo, help footer, Metadata Off, Basic/system and other ratios remain unchanged. No output timing changes.

## Original metadata styling

Reviewed upstream `aspect-ratio-16-9.xml`, original 4:3 declarations and shared `theme.xml`: icon/value pairs, rating stars, Roboto Bold and metadata palette. Reuse existing `metadata-icon-{releasedate,players,playcount,gametime,lastplayed,genre}.svg` assets; no invented icons or label/value table. Font size `.033333333333333` is the upstream default release/play-time font size, fixed here across presets to fit compact rows.

Five row centers: `.58, .64, .70, .76, .82`. Release date and rating share the first row; play time and play count share the second. The following rows contain last played, players and genre (players directly above genre). Play time has width `.16` on the shared row; players has width `.36`. Left icons x `.55`, values x `.59`; play count icon/value x `.78`/`.82`. Rating is right-anchored at `.95`. Value boxes are `.045833333333333` screen height; icons fit `.03125 .041666666666667`; dates use `YYYY-MM-DD`. The first row begins below the original media/marquee region, which ends no later than `.541666666666667`; the final row ends before `.86`, above the help footer.

## Native component semantics

Inspected Batocera ES revision `b2ceb55a7e3d205a11f055b7d93c8be50cd6f9c9`:

- `DetailedContainer.cpp`: native `md_gametime` is play time; release and last played are `datetime`, rating is `rating`, remaining values are `text`. Preserve native data bindings and missing-value behavior.
- `DateTimeComponent.cpp`: supports `format`, `displayRelative`, font and color. Both dates set `%Y-%m-%d`, `displayRelative=false`; no unsupported text-only properties on datetime.
- `TextComponent.cpp`: bounded single-line values use native ellipsis with `multiLine=false`, `autoScroll=none`.
- `RatingComponent.cpp`: width zero derives five-star width from pixel height; bounds tests include that actual width.
- `ThemeData.cpp`: source-order includes and conditional overrides are retained. Resolver selects automatic dispatch but does not exercise native aspect detection.

## Verification

### Cumulative playtime (current candidate)

Only enabled 4:3 Detailed metadata replaces native `md_gametime` with the `extra="true"` text component `game-gametime-totalhours`. The native field is hidden there only. All its resolved geometry, fonts, palette and clock icon remain identical; RA on/off is independent. No new subset or helper changes. Stock Batocera 42 ES pin: `4adf26b43900d1a33887af6d8af3da2e99e398a5`.

Verified `ThemeData.cpp:228–275` text schema and `1681–1687` automatic `text_binding` registration: **there is no `<boundtext>` element**. `BindingManager` substitutes integer `game:gametime`, evaluates compound expressions, and excludes built-ins; `DetailedContainer` refreshes extras before its same-state early return. Therefore a separate text extra is necessary. Selection refresh still needs on-device QA.

Expression (XML escapes `>>` as `&gt;&gt;`):

```text
"" + (({game:gametime} / 3600) >> 0) + "h " + ((({game:gametime} / 60) >> 0) - ((({game:gametime} / 3600) >> 0) * 60)) + "m"
```

Test-first: three expected failures (native visibility, strict approved-tree transform, hidden-native preview) before implementation. Full pytest: **96 passed, 104 subtests passed**. Scoped tree comparisons preserve every unrelated node/property; activation coverage includes automatic/manual 4:3, metadata modes, help/font presets and RA states. Metadata preview validator and whitespace check pass.

Actual unchanged pinned MathExpr/HtmlColor C++ sources were rebuilt in `/tmp/playtime-probe` (see its `REPORT.md` for build/stubs/source hashes). Run `python tools/check_playtime_parser.py /tmp/playtime-probe/probe` against that binary: 0/59/60/3599/3600/9300/86400/172800/177300/3599999 seconds pass, including `0h 0m`, `48h 0m`, `49h 15m`. This is a separate native-parser check, not a Python evaluator or a dependency of portable pytest. Accepted float limitation: 16777259 seconds gives `4660h 21m` instead of exact `4660h 20m`; no claim of unrestricted minute accuracy.

Static renderer explicitly maps the new extra to a known fixture (`9300` seconds → `2h 35m`); it does **not** evaluate live bindings or arbitrary expressions. Comparative C64 previews in `previews/playtime-total-hours/` use the verified `49h 15m` sample, with RA off/on and 640×480/320×240 coverage. No Recalbox artwork. These are static compositions, not native captures. Check game selection, zero playtime, long values/ellipsis and CRT readability on-device. Only runtime file to update is `aspect-ratio-4-3.xml`; restart ES, with no RA helper resync.

```sh
python3 -m pytest tests/ -q
python3 tools/render_metadata_panel.py
python3 tools/validate_metadata_preview.py
git diff --check
```

Test-first: replacement tests failed with 27 expected assertion/subtest failures on the rejected smaller-media/table candidate. After correction, seven test methods pass. Tests compare entire resolved media components against upstream across help/artwork/metadata settings, verify seven-field visibility, excluded fields, original assets/colors and bounds. Retained tests cover unaffected modes and byte-identical shared/other-ratio files. Git baseline history is required; the resolver sanitizes pre-existing upstream bare ampersands in memory, without modifying shared XML.

Current preview outputs: `previews/original-style/`. Static Pillow/CairoSVG compositions use actual resolved geometry/assets and sample Super Metroid metadata; source screenshot is from libretro thumbnails. No gameplay or native frontend is running. Legacy preview directories show superseded candidates. Preview validation checks sample values, six icons, bounds, non-overlap and truncation at 320×240 and 640×480.

## Hardware palette

The existing `commodore-64` option uses C64 breadbin / 1702 exterior colors. The preview-approved palette retains the existing option name.

Native selector support was checked against Batocera ES `37d70f3e46282ba431a64813347cf5b0431bbbfb`: `ThemeData.cpp` declares textlist `selectorImagePath`, and `TextListComponent.h` sets the image size to list width × selector height, with row height derived from `lines`; white `selectorColor` preserves the SVG's colors. The SVG has a transparent body and five muted colored segments along the bottom of the first fifth of the row. Only this palette's textlist override is added; no font, icon, media or row geometry changes.

Test-first evidence: revised hardware-palette and selector expectations failed against the blue palette (two palette assertions and one preview test), then all 12 regression methods passed. Strict baseline comparison removes only the existing palette registration/variables and the exact two-property, palette-gated selector block; every remaining XML node/comment/attribute is preserved. The layout comparator now permits only the requested six metadata icon/value position changes and two value-width changes against the approved revision; all media assertions remain intact. Contrast ratios: brown metadata/beige 8.25:1, muted metadata icons/beige 4.66:1, cream list/brown 10.74:1, selected gold/brown 8.86:1, gray help icons/charcoal 7.84:1. Existing white menu text on the brown selector is 7.51:1.

Generate with `python tools/render_metadata_panel.py --scheme commodore-64`. Both 320×240 and 640×480 previews in `previews/commodore-64/` were inspected: seven fields present, original media geometry, understated rainbow underline, no obvious sample clipping or overlaps. The regenerated `geometry.json` records the requested metadata reorder only. The ordering regression first failed with 36 expected subtest failures, then all 14 test methods passed. Both default and hardware-palette sample validators pass at 320×240 and 640×480, including the complete `2 h 35 mn` value in the narrowed shared-row box. Tests check the actual selector accent pixels in the selected row, not game art. These are static approximations, not native captures; SVG filtering/subpixel placement, long or translated values, native system/menu/splash screens and physical CRT readability remain unverified.

## RetroAchievements integration checks

The optional integration is documented in [RETROACHIEVEMENTS.md](RETROACHIEVEMENTS.md). Theme registration initially failed its new tests, then passed after implementation. The helper was tested with an explicit local HTTP fixture server and subprocess CLI calls, not fabricated live API results. Review regressions reproduced wrong vertical anchoring, stale extras after account/game remapping, removed mappings, and partial installation on an unsafe example path; these were corrected and rerun. The revised full suite has 43 passing tests, including strict opt-in geometry guards and the prior metadata/palette guards. Latest bottom-bar regressions were observed failing before implementation. Players stays at x=.78/.82, y=.70 beside Last Played; Genre moves to y=.76. The actual generated SVG track occupies x=.55–.95, y=.815–.870 (256×26 pixels at 640×480), below metadata and above the unchanged footer. Native white count text is centered at (.75, .8425) on a dark .14×.055 background badge with higher zIndex; there is no separate count row. The pinned Batocera 42 ThemeData.cpp text schema and TextComponent.cpp applyTheme implementation both support backgroundColor. The renderer respects exact extra origins, colors, background and zIndex. A pixel test verifies the badge and centered count in both palettes/resolutions, with clearance from Genre and footer. SVG aspect-ratio regression prevents a taller image box from merely letterboxing the old thin track. RA-off and other views/ratios remain guarded; asset ownership/cache code is unchanged. Zero, full, fractional and separate softcore/hardcore fills are tested, along with content-addressed asset ownership, bounded cleanup and offline retention. New static previews at 640×480 and 320×240 in both palettes use generated XML **and the helper-generated SVG asset**, and sample values pass no-truncation/no-overlap checks. All four previews were visually inspected. See [primary labeled preview](../previews/retroachievements-bottom/commodore-64-480-labeled.png); the 55-pixel caption is outside the 640×480 framebuffer. No native Batocera/account test was performed. At 320×240 text remains inherently small; physical CRT legibility is unverified.

```sh
python3 -m unittest discover -s tests -v
python3 tools/render_ra_preview.py
python3 tools/validate_metadata_preview.py
```

## Historical dark-track correction (superseded by refinement below)

The old SVG painted its full unfilled track `#77736a`; the centered `#292621` native text badge interrupted it, producing pale patches after the rainbow and at the right end. This was an empty-progress track, not another gradient stop or stroke. The track now matches the subdued badge color. Raster tests also exposed transparent end strips from default SVG aspect fitting when 26.4 pixels rounds to 26: `preserveAspectRatio="none"` makes the asset fill the specified rectangle. Regression tests sample top/middle/bottom and right-edge pixels at zero/partial/full progress.

Latest verification: `python -m pytest tests/ -q` → **47 passed, 104 subtests passed**. New track, registration, custom-loading and gallery tests were witnessed failing first. `python tools/render_ra_preview.py --all-palettes` renders all **8 registrations** directly from `theme.xml`: Default, Light, SteamOS, SNES, Famicom, OLED, Commodore 64, Custom. Every palette variable is checked against its selected `colors.xml` block; unresolved properties and unknown scheme names fail loudly. Custom explicitly loads the shipped `resources/customizations/colors.xml` template, whose default colors intentionally match Default—not a silent missing-file fallback and not a capture of the user's on-device custom file. A distinct override fixture verifies Custom really loads, and a missing custom file raises an error.

Latest gallery: `previews/retroachievements-palettes/`, two full-size 2×2 contact sheets and eight raw 640×480 framebuffer images with corresponding labeled 640×535 canvases. Labels sit outside the unchanged framebuffer. Both sheets were visually inspected: all seven native fields, original media, centered count and clean dark remainder are intact; no new sample clipping. Inherited low-contrast unselected text in several palettes is unchanged. `manifest.json` records resolved variables, provenance, geometry and pixel hashes (seven distinct designs; Custom template equals Default). `fixture/sample.xml` references the actual generated SVG used by all renders. These remain static approximations with fictional 12/40 progress; native Batocera/CRT behavior is not verified. No commit or push.

## Latest metadata-height / palette-bound RA refinement

The older white-count/dark-badge and .055-height descriptions above are historical,
not the current candidate. [Current specification](RETROACHIEVEMENTS.md) takes precedence.
New bindings/geometry tests failed before implementation. The track now uses a white
SVG tinted by `${gamelistListTextlistBackgroundColor}`; the separate transparent
rainbow SVG remains proportional. The latest approved count refinement uses
`${gamelistListTextlistUnselectedColor}` (normal sidebar text), font
`${themePath}/${fontBold}`, fontSize `.027777777777777` (16.67% smaller), without
a background badge or shadow. Metadata typography is unchanged. Height .045833333333333
matches normal metadata (22px at 480p, 11px at 240p); center y=.837916666666667.
Glyph fit, full count width, metadata clearance, footer whitespace, exact edges,
all eight palette-resolved sidebar pixels and native XML bindings are tested.
Both generated image paths participate in the ownership journal and full-manifest
cleanup; offline and repeated-refresh tests guard retention and bounded asset counts.
Setup/example no longer install stale template overrides. Image.open warnings in
the palette gallery tests were fixed with context managers.

Previous refinement execution: `python3 -m pytest tests -q` → **50 passed, 104 subtests passed
in 18.53s**. `python3 tools/validate_metadata_preview.py` → both palettes' seven
sample values and six icons fit at 240p/480p without truncation/overlap.
`git -c core.whitespace=cr-at-eol diff --check` passed. Pinned ThemeData source was
re-fetched and byte-matched to the inspected cache (SHA256
`a0073b73d1747fd75e4216ca3bb9152b10e7fa2e3492ce2f3cb358334a6b6c14`).

Pinned ES42 ThemeData.cpp was inspected: clone copies variables; appendFile keeps
them; placeholders resolve before native COLOR/PATH parsing. Native palette switches
therefore do not depend on network/cache regeneration. Generated font paths explicitly
anchor relative fontBold to themePath, rather than the appended extra directory.

Latest gallery: `previews/retroachievements-final-text/contact-sheet-1.png` and
`contact-sheet-2.png`, plus eight raw 640×480, labeled 640×535 and secondary 320×240
images. Both sheets were visually inspected. No pale right-end artifact, badge patch,
metadata overlap or new sample clipping. **Important:** sidebar text alpha is
preserved. Famicom remains faint (1.80:1 on the empty track), whereas C64 ivory now
has 10.74:1 empty-track contrast. At full progress both lose contrast over the
yellow/green fill (Famicom 1.11–1.17:1; C64 1.29–1.61:1). These are full-coverage
glyph calculations, not anti-aliasing or CRT certification. Zero/sample/full
crops were also inspected; no unrequested badge/outline/shadow was added.
Custom uses the explicitly labeled shipped template. These are actual generated
component compositions with fictional counts, not native screenshots.

Final-text verification: `python -m unittest discover -s tests -v` passed all
51 tests, including setup-output equality to defaults, count width/height at both
resolutions, ownership/cache lifecycle and all palettes. The new color tests were
observed failing against the previous metadata binding before the implementation.
`python tools/validate_ra_final_text.py` validates all gallery sizes and 12
zero/sample/full fixtures and records glyph dimensions and contrast in
`previews/retroachievements-final-text/contrast.json`. The sample count uses
17px/9px scaled fonts with 13px/8px glyph heights at 480p/240p respectively;
integer scaling quantizes the nominal 16.67% reduction. Existing private template
overrides require removal plus one sync; fresh setup's empty template is tested.

## Remaining device checks

No native Batocera/Pi 5/Commodore 1702 rendering was performed. Static font metrics and bounding boxes cannot prove analog readability, overscan, native text rasterization or video/marquee layering. Long real-world values may ellipsize; test long times, translated genres, missing dates, never-played games, folders and missing artwork/video on-device. Original icon color/contrast is preserved, not certified as CRT-optimal. Screenshot previews show Image mode; exact geometry preservation tests also cover cropped image, boxart, logo and video components.

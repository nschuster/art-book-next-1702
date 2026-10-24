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

```sh
python3 -m unittest discover -s tests -v
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

## Remaining device checks

No native Batocera/Pi 5/Commodore 1702 rendering was performed. Static font metrics and bounding boxes cannot prove analog readability, overscan, native text rasterization or video/marquee layering. Long real-world values may ellipsize; test long times, translated genres, missing dates, never-played games, folders and missing artwork/video on-device. Original icon color/contrast is preserved, not certified as CRT-optimal. Screenshot previews show Image mode; exact geometry preservation tests also cover cropped image, boxart, logo and video components.

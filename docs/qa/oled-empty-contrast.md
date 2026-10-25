# OLED empty-state contrast candidate

Unpublished; no commit/push or device access. Only the registered `oled` / **OLED** palette changes visually.

- Empty rating star: native `unfilledColor=777777`, replacing inherited `ffffff33` (white at 20% alpha, effective #333333 on black). Filled-star tint and both original star SVGs are unchanged. The original unfilled SVG is a very thin white outline, so antialiased edge pixels remain dimmer than the nominal tint.
- Empty RA track: #000000 → #303030, leaving sidebar and main surface #000000. Generated white track now binds `${raProgressTrackColor}`. `progress-colors.xml` inherits the final sidebar for all other schemes, including a real Custom override, and overrides only OLED.
- Nominal sRGB contrast against black: star 1.6621:1 → 4.6895:1; track 1:1 → 1.5911:1. This is a deliberately subtle track, **not** a claim of 3:1 accessibility compliance. Count styling is unchanged and remains muted; no badge/outline added.

## Native source evidence

Re-fetched and byte-compared Batocera 42 ES pin `4adf26b43900d1a33887af6d8af3da2e99e398a5` against inspected local sources:

- `ThemeData.cpp:398–427`: rating schema supports `unfilledColor` as COLOR; `RatingComponent.cpp:230–240` applies it independently, otherwise inherits `color`.
- `ThemeData.cpp:785,1172–1184,parseTheme`: variables are pre-parsed before includes. A parent variable block merely placed after colors would NOT safely inherit final colors. The separate include is intentional, placed after ordinary and Custom palette includes.
- `ThemeData.cpp:2649`: clone copies `mVariables`; `appendFile` parses generated extras against those globals. Track uses the existing supported image/color property, no invented schema.
- Source SHA256: ThemeData `a0073b73d1747fd75e4216ca3bb9152b10e7fa2e3492ce2f3cb358334a6b6c14`; RatingComponent `525f8b675bd28c6b6aa8fc90c027ae1dda7af89529a2b8ec3a0d547247411bd3`.

## Verification and previews

RED: two targeted tests failed for absent empty-star tint and dedicated track variable; strict include-order comparison also failed before moving defaults to their native-safe include. GREEN: **113 passed, 104 subtests passed**; whitespace diff check clean. Exact historical-tree guards now permit only the two intended theme additions. `colors.xml` remains byte-identical to the task-entry tree.

`previews/oled-empty-contrast/` contains before/after 640×480 and 320×240 native-size static frames, with sample 12/40 and 0/40 achievements and a rating containing four filled stars plus one empty star. Primary comparison: `comparison-480-12.png`; secondary zero-progress: `comparison-240-0.png`. See `manifest.json` for geometry and contrast. Compared all seven other registered palettes at 640×480: pixel-identical to task-entry renders. At both sizes and both counts, OLED changed pixels are confined to the empty-star and track/count regions. All palette definitions, trophy size/gap, count/metadata fonts, media geometry and rainbow remain unchanged. RA-off gets only the intended empty-star improvement, never a progress element.

Inspected both comparison images: empty outline is clearer, the full track is now discernible, and layout is unchanged. Native rendering/CRT/OLED physical readability is unverified; Pillow/CairoSVG antialiasing and native text may differ. These are fictional static fixtures, not account data or device captures. Count and other pre-existing dim metadata are intentionally outside scope.

## Deployment implication

Update theme (including `progress-colors.xml`) **and** helper, then regenerate existing owned per-game extras once so their old sidebar binding becomes `${raProgressTrackColor}`. Reload/reselect the theme/game as necessary. Do not rerun successful private configuration or change credentials. Subsequent palette switching resolves the new variable without another sync. Device target remains `/userdata/themes/art-book-next-1702-retro-achivements`; no device changes were performed.

# Canvas left-column / all-palette review

Local unpublished candidate. User authorized refining the enabled carousel; no commit, push or installation performed. Source rights conflict remains unresolved.

## Scope

Only `console-showcase.xml` runtime geometry changes: original logo is left-anchored at x=.07, center y=.22, maximum .43 × .17; hardware is left-anchored at x=.07, center y=.535, unchanged maximum .43 × .36. Both use origin `0 .5`. Missing-logo/name and missing-art fallbacks follow that column; the name font is reduced to .03 to fit the narrower fallback box. Right-column metadata and every other component property are retained. Off stays first/default and existing resolved-baseline tests cover all artwork presets, both help states, 4:3/manual/automatic-dispatched and 16:9. Non-system views remain unaffected.

Hardware files are the existing lossless alpha-cropped PNG imports of Canvas WebP assets, not recolored drawings. Host SVG logos remain byte-identical and use actual multiplicative `systemLogoColor`. No Canvas logos, backdrop or collage imported. C64 preview image and alpha-bounded visible rectangles share left x=45 at 640×480 and x=22 at 320×240. Original/custom SVG viewBox transparency can offset visible ink for other systems: rectangle alignment is guaranteed, universal optical alignment is not. Assets were not trimmed or distorted to conceal that limitation.

## Gallery

`previews/canvas-carousel-left-palettes/` is new; the initial `previews/canvas-carousel/` remains unchanged.

- [640 sheet 1](../../previews/canvas-carousel-left-palettes/palettes-640-sheet-1.jpg): Default, Light, SteamOS, SNES.
- [640 sheet 2](../../previews/canvas-carousel-left-palettes/palettes-640-sheet-2.jpg): Famicom, OLED, Commodore 64, Custom (shipped template).
- [320 sheet 1](../../previews/canvas-carousel-left-palettes/palettes-320-sheet-1.png) and [320 sheet 2](../../previews/canvas-carousel-left-palettes/palettes-320-sheet-2.png).
- Sixteen individual native-size PNG frames, identical C64 fixture across all palettes; 320×240 composed independently, not frame-downsampled.
- `manifest.json` records resolved surface/logo/footer colors, tint, paths, image/ink bounds and text-fit measurements. Palette registrations are enumerated from actual `theme.xml`; Custom explicitly loads `resources/customizations/colors.xml` after defaults.

Reproduce: `python tools/render_canvas_carousel.py --all-palettes --output previews/canvas-carousel-left-palettes`

Static Pillow/CairoSVG compositions, not native ES GUI captures. Actual runtime assets/XML/fonts are used; font shaping, image sampling and rounding can differ from the frontend. Native help prompts are represented by labeled sample text; controller/clock/network live state, counts and playtime are omitted. No device/CRT validation claimed. All C64 metadata strings fit at both sizes without overlap; 240p detail and typography are small. Default, Light, OLED and Custom intentionally have similar system surfaces; no invented palette differences were introduced.

## Verification

- RED before XML/renderer edits: `python -m pytest tests/test_canvas_carousel.py -q` → 3 failed, 11 passed (missing left origin, missing left-column geometry, absent palette enumeration).
- Additional RED caught discarded help-text alpha (`255` where default ffffffaa over black must not exceed `170`). Fixed by compositing text layers, not changing theme colors.
- Hardware equality compares only fully opaque source pixels: translucent shadows correctly composite differently against different surfaces and must not be treated as unwanted recoloring.
- GREEN targeted: 14 passed.
- Full native environment: `BATOCERA_ES_SOURCE=/tmp/ra-es-source BATOCERA_LAUNCH_EXPR_PROBE=/tmp/launch-expression-probe/launch-probe BATOCERA_SVG_RASTER=/tmp/eudora-native/raster python -m pytest tests -q` → **255 passed, 1 skipped, 104 subtests passed** in 73.62s. Skip is unavailable supplied Eudora archive; expression/raster/source paths enabled.
- `git -c core.whitespace=cr-at-eol diff --check` passed.
- SHA-256 preservation snapshot: 72 files (initial Canvas gallery, theme.xml, controller-related files) unchanged.
- Visually inspected both primary 2×2 sheets and independent 240p sheets; no fixture clipping or overlap. Final regenerated sheet confirms palette-alpha footer colors.

Native source schema/factory checks are against pinned Batocera ES `4adf26b43900d1a33887af6d8af3da2e99e398a5`. They and the native helper probes do not constitute on-device carousel screenshots or redistribution clearance.

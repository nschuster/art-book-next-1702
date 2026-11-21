# Canvas carousel: values-only metadata candidate

User correction: “No need to display the name again on that side and no need for the headings on the metadata as well.”

## Scope and layout

Only the optional enabled system carousel's right metadata changes. Removed the manufacturer text component and ARCHITECTURE / CPU / RAM / LAUNCH PRICE heading components, plus the `Released` prefix. Retained the exact existing type, year, architecture, CPU, RAM and launch-price bindings and values, including market/currency and intentional Unknowns. No source research, data corrections, generator changes or asset edits.

Right column remains x=.55–.95. Type is modestly bold at y=.26; year at .31; architecture/CPU/RAM at .405/.46/.515; launch price at .61. All boxes are .04 high. The type/year pair, specification group and price use whitespace rather than headings. The text region ends at .65, optically balancing the left hardware rather than filling the former heading slots.

Left logo remains origin `0 .5`, position `.07 .22`, maxSize `.43 .17`; hardware remains origin `0 .5`, position `.07 .535`, maxSize `.43 .36`. Other components, includes, palettes and Off behavior remain unchanged. No changes to theme.xml, system-playtime.xml, RA helpers, Ports, main README or historical gallery files.

## Artifacts

All paths relative to repository root:

- `previews/canvas-metadata-values/commodore-64-c64-640x480.png` — primary; saved and visually inspected early.
- `previews/canvas-metadata-values/commodore-64-c64-320x240.png` — independently composed, not downsampled.
- `previews/canvas-metadata-values/palettes-640-sheet-1.jpg` and `palettes-640-sheet-2.jpg` — all eight registered palettes, inspected.
- `previews/canvas-metadata-values/palettes-320-sheet-1.png` and `palettes-320-sheet-2.png` — independent low-resolution versions.
- `previews/canvas-metadata-values/representatives-640.png` and `representatives-320.png` — SNES, PlayStation, original Game Boy and unlisted-system fallback. Low-resolution sheet inspected.
- `previews/canvas-metadata-values/manifest.json` — 24 individual frames with resolved values, dimensions and fit/truncation evidence.
- `previews/canvas-metadata-values/README.md` — evidence limitations and source references.

Regenerate only this new gallery:

```sh
python tools/render_canvas_carousel.py --metadata-refined --output previews/canvas-metadata-values
```

The existing CLI flag is retained for compatibility; it renders the current XML, now values-only. Custom uses the shipped template, not device configuration.

## Verification

Strict RED/GREEN:

1. Replaced only the now-rejected manufacturer/heading hierarchy regression with exact six-value component/binding, spacing, safe-region and full-glyph-fit assertions. Both resolution cases failed on the unwanted manufacturer/label components before XML changes, then passed.
2. Added isolated gallery coverage/documentation regression using pytest `tmp_path`; witnessed failure on the old gallery heading before updating renderer output documentation.
3. `python -m pytest tests/test_canvas_metadata.py tests/test_canvas_carousel.py tests/test_canvas_price_audit.py -q` → **24 passed**.

These retain imported-byte/source-provenance guards, sourced overlay/alias tests, generator reproduction, full system inventory fit, palette contrast, native schema/factory checks, other-view and Off-state preservation, actual left geometry and safe-region coverage. Gallery tests write only to temporary directories.

A pre-edit SHA-256 inventory confirmed **1,635 preexisting preview/source files unchanged** after renders and scoped tests. All 24 new frames passed full-string fit/no-truncation checks. Compared corresponding old refined-gallery frames: the entire left region x<.53 and footer region y>=.8 are pixel-identical. The unchanged source overlay retains its existing Unknowns; removal of headings does not imply new historical verification.

Primary frames are readable with deliberate group spacing; 320×240 text is naturally small and native CRT readability remains unverified. Unknown systems deliberately display repeated Unknown values now that field headings are absent. Static Pillow/CairoSVG approximations are not native EmulationStation captures; no live controller/status/count/playtime, native transitions or CRT proof. Source artwork redistribution rights remain unresolved. No commit, push, installation or device changes. Full shared-tree integration suite belongs to the parent workstream after concurrent edits settle.

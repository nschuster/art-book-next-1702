# Refined optional carousel metadata

Local unpublished candidate. Only enabled Console Hardware & Info system view is redesigned. Logo/hardware positions, sizes, host assets, palettes, other views and Off mode are preserved.

## Presentation

Right column has bold manufacturer, smaller system type/release, then separately labeled architecture, CPU, RAM and launch price. Opaque host foreground is retained. Labels are deliberately small; 640×480 is primary. Independently rendered 320×240 frames are legible in static previews but physical CRT readability is unverified.

`tools/build_canvas_specs.py` generates additive `specs/*.xml` from field-level evidence in `_inc/canvas-hardware/specs.json`. Original imported metadata, source manifest and artwork bytes remain unchanged. Unknown is an evidence gap, not a claim that the historical fact is unknowable. RAM means main/work RAM, not summed video/audio memory. Source classifications can describe mixed architectures; not every internal bus has the displayed bitness.

## Coverage and source limits

Across 24 imported systems: 16 populated architecture fields, 5 CPU fields, 5 RAM fields, 4 launch-price fields. All other new fields are explicitly Unknown. This is implementation of the panel, not a complete historical database. Existing manufacturer/type/year remain inherited; e.g. SNES year 1992 reflects the imported regional value rather than first worldwide release. Artwork may depict later hardware/controllers. Generic Amiga-family facts remain Unknown rather than applying an A500 specification to A1200 aliases.

C64 US $595 has independent Computer History Museum corroboration: https://www.computerhistory.org/timeline/1982/ . PlayStation JP ¥39,800 corrects the inherited unsupported ¥37,000 using https://www.videogameconsolelibrary.com/pg90-playstation.htm . These are retrospective sources, not inspected original price announcements. Other populated prices remain attributed to Canvas descriptions. SNES/Game Boy exact launch prices are unverified; live Nintendo legacy catalog pages show later prices next to original release dates and are not launch-price evidence.

## Reproduction and verification

```
python tools/build_canvas_specs.py
python tools/render_canvas_carousel.py --metadata-refined --output previews/canvas-metadata-refined
PYTHONDONTWRITEBYTECODE=1 BATOCERA_ES_SOURCE=/tmp/ra-es-source BATOCERA_LAUNCH_EXPR_PROBE=/tmp/launch-expression-probe/launch-probe BATOCERA_SVG_RASTER=/tmp/eudora-native/raster python -m pytest tests -q -p no:cacheprovider
```

Final full suite: **264 passed, 1 skipped, 104 subtests passed**. The skipped check needs the unavailable supplied Eudora archive. Native schema/source and parser/raster probes are enabled; this is not native GUI verification. Parent price-audit RED: 2 failures before price/provenance correction; final suite passes them. Test coverage includes all imported systems/aliases at both sizes, all-palette contrast, source asset preservation, Off-mode preservation, generated-data reproducibility and long-value ellipsis.

Independent comparisons confirm left artwork and footer pixel identity for 16 palette/resolution image pairs against the prior delivered gallery. Original gallery/source hashes and theme.xml/controller-status.xml/gamesplash.xml hashes remain unchanged. Whitespace check passed. Final C64 palette sheet and representative sheet were visually inspected after corrected price regeneration.

## Artifacts

`previews/canvas-metadata-refined/`: eight-palette C64 frames and sheets, SNES/PSX/Game Boy/unknown frames and sheets, manifest with actual text fit measurements. Custom is the shipped template, not device custom settings. Static Pillow/CairoSVG approximations using runtime XML/assets/fonts, not Batocera captures. Sample help; live indicators/count/playtime omitted. Older galleries are historical and untouched.

No commit, push or device installation. Existing Canvas artwork licensing conflict remains unresolved; local implementation/preview approval is not redistribution clearance.

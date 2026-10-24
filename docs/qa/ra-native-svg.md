# Batocera 42 native RA rendering investigation (candidate, not deployed)

Inspected frontend revision `4adf26b43900d1a33887af6d8af3da2e99e398a5` in
`batocera-linux/batocera-emulationstation`, and the actual CRT photo. The photo
shows a blue/cyan rectangle and no readable count. No device was available.

## Proven SVG defect and scoped correction

`external/nanosvg/nanosvg.h` defaults gradients to object space (2573), but
`nsvg__createGradient` (848–865) passes endpoints through pixel coordinate
conversion. Unitless `x2="1"` therefore produces a one-unit gradient rather than
a gradient spanning the shape. Use percentage endpoints `0%` to `100%`.

Compiled the exact pinned `nanosvg.h` and `nanosvgrast.h` with g++, parsed the
actual helper-generated partial-progress SVG (12/40), and rasterized with the
same scale used by `es-core/src/resources/TextureData.cpp:146–152`, at 256×22.
Center-row RGB at x=20,40,60 before: all `(82,126,176)` (final blue stop).
After: `(223,142,57)`, `(218,194,84)`, `(103,151,107)` (orange/yellow/green).
Pixels past the fill remained transparent. The white track remained white.
This exercises the native SVG library, NOT the complete native frontend or CRT.
Scratch sources, original/fixed SVGs and executable: `/tmp/ra42-research/`.

The change modifies only SVG endpoint syntax: same stops, proportional width,
22px bar height at 480p, count font/size/colors and metadata geometry. Asset
content addressing automatically gives the corrected SVG a new filename.
Regression was observed failing before implementation; full pytest afterwards:
92 passed, 104 subtests passed.

## Rejected hypotheses, backed by pinned source

- Lost globals: `DetailedContainer.cpp:776–782` clones the active theme before
  append; `ThemeData.cpp:2647` copies `mVariables`. `appendFile:2674` changes
  `currentPath`, not `themePath`. Variables are not discarded on append.
- Implicit cyan image tint: `ImageComponent.cpp:37–38` defaults both tint ends
  to white; generated rainbow explicitly supplies `FFFFFFFF` anyway.
- XML order covers count: extras get ALL properties in `ThemeData.cpp:2271–73`;
  DetailedContainer adds them to the parent and sorts at 532–536 (its header
  delegates addChild to the parent). `GuiComponent.cpp:357–361` sorts ascending
  zIndex. Generated track=99, fill=100, count=101 puts count on top.
- Unsupported text properties: `TextComponent.cpp:573–704` consumes text,
  center alignment, color, single-line and themed font. These generated
  properties are supported. No justified typography workaround was made.

## Still unresolved / required device evidence

The gradient defect explains the solid blue fill but does NOT establish why
there is no readable count. Need the device's selected-game generated XML
(and its referenced SVG) to check actual count, template overrides, old output,
asset identity and bounds before changing text. Installing a helper does not
regenerate existing XML/assets. Do not claim this fully fixes the photograph.

After installation, regenerate only the selected game's extras using existing
`--system gb --rom '<actual gamelist path>'` options; this fetches at most its
one game ID, not all games (full mapping reconciliation still runs). Obtain the
actual ROM path first; do not guess it from the display title. No cache-only flag
or full-library sync is needed for this narrowly targeted verification.

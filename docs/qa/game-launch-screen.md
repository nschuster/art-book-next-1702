# Selected-game logo launch screen QA

## Current candidate: supplied Eudora hardware artwork

`gamesplash.xml` (not startup `splash.xml`) displays the selected game's marquee/logo above subdued **supplied hardware/controller artwork**, on the selected palette background. **SNES is a controller, not a console.** Other source drawings depict controllers, handhelds and computers. No cover, screenshot substitution, progress indicator or duplicate title. Native game title appears only when the marquee path is empty or nonexistent; corrupt existing images cannot be detected by the filesystem expression.

This asset replacement does not change native launch XML, geometry, bindings, fonts or palette definitions. Browsing artwork/logos, RA, startup and all unrelated work are unchanged. Custom uses the existing distribution-specific colors file; contrast of user overrides is not guaranteed.

## Native source and binding verification

Batocera 42 ES pin **`4adf26b43900d1a33887af6d8af3da2e99e398a5`**, available at `/tmp/ra-es-source`. Tests inspect pinned Git objects, not an unverified current branch. [Pinned source](https://github.com/batocera-linux/batocera-emulationstation/tree/4adf26b43900d1a33887af6d8af3da2e99e398a5).

- `FileData.cpp` launches with the game's image/name/Bindable; `Window.cpp` constructs Splash then updates the title.
- `Splash.cpp` loads root `gamesplash.xml`, view `splash`, and permits bound background paths. Overriding built-in `background` with `{game:marquee}` removes the initial screenshot, including absent marquee.
- Label `!exists( {game:marquee} )` uses real native MathExpr, not an invented condition. BindingManager quotes Path strings, including empty paths; Null substitutes no characters. Whitespace is intentional. Window's later title update does not undo bound visibility. Do not bind title text: Window overwrites it.
- Hardware expression remains `"${themePath}/_inc/launch-hardware/" + {game:system:name} + ".svg"`. Nested Bindables resolve the source game's system, not the collection/group. Unknown IDs have nonexistent paths and no image, with no misleading fallback. Collection behavior still needs device QA.
- Both native progress images remain explicitly invisible; normal launch percent defaults to -1.
- Splash overwrites component opacity each frame. Intrinsic SVG root `opacity="0.45"` survives this, multiplied by `${gamelistListDescriptionColor}`.

Actual compiled pinned MathExpr execution in `/tmp/launch-expression-probe/launch-probe` verifies existing-path visibility 0, nonexistent/empty/Null visibility 1, and exact hardware concatenation for snes/c64/unknown-system/ports. Supporting string methods are harness implementations; exists uses POSIX stat rather than native FileCache. This executes the evaluator, not the entire native frontend.

## Exact inventory, attribution and unresolved rights

**52 hardware-system source `controller.svg` files plus four aliases (56 runtime IDs)** replace all earlier invented drawings. No geometry was redrawn, cropped, rotated or normalized to the former 200×100 canvas. `_inc/launch-hardware/manifest.json` records exact supplied ZIP SHA256, archive-member paths, source/output SHA256, original viewBoxes, exclusions and alias mappings.

Aliases: `genesis → megadrive`, `sfc → snes`, `jaguar → atarijaguar`, `atarilynx → lynx`. Excluded software/application/collection and arcade-emulator sets: doom, favorites, fba, fbneo, imageviewer, kodi, mame, ports, scummvm, zmachine. All remaining hardware-system `controller.svg` files are included. Unsupported invented drawings are removed, including 3DS, DS, Switch, Wii U, Vita, GC, Wii, PS2 and PSP. Source directories without this artwork are not covered.

Eudora credits **AmadhiX** for all XML, sounds and some images; **Carbon by Eric Hettervik**, based on **Simple by Nils Bonenberger**, supplied most logos/line art. The entire source readme is preserved unchanged in `_inc/launch-hardware/SOURCE-README.txt`. Its separately stated background-texture/font licenses do not establish line-art rights. **Redistribution permission remains unresolved.** Repository inclusion is not a license grant. Do not assign the enclosing theme's original-art CC license to these borrowed assets.

## Unchanged geometry and paint normalization

Logo origin `.5 .5`, center `.5 .37`, maxSize `.78 .40`. Fallback title center `.5 .37`, origin `.5 .5`, size `.84 .16`, Roboto-Bold `.05`, centered multiline. Hardware center `.5 .73`, origin `.5 .5`, maxSize `.36 .22`, zIndex 6.

Hardware aspect-fits source-specific proportions inside 230.4×105.6 at 640×480 and 115.2×52.8 at 320×240. Centers remain (320,350.4)/(160,175.2). Native fractional rounding may differ from static previews. No video mode, pixel-aspect or transition-duration changes.

Only explicit source pale-gray fill/stroke paint is normalized to white for multiplicative palette tint, with root opacity `.45` added. All geometry, dimensions, viewBoxes, transforms, drawing order and metadata remain intact. Most line work consists of **filled outline paths**, not new uniform strokes. NanoSVG inherits opacity per shape; overlapping shapes can composite above .45, unlike browser group-opacity flattening. Thin source detail is intentionally preserved and can be faint at 240p. No stroke thickening or invented console substitutions.

## Executed replacement evidence

- RED: `PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_gamesplash.py -q -p no:cacheprovider` → **2 failed, 10 passed, 1 skipped**: missing new provenance/license contracts; `/tmp/eudora-red.txt`.
- GREEN with `BATOCERA_LAUNCH_EXPR_PROBE=/tmp/launch-expression-probe/launch-probe` → **13 passed**. Archive-backed checks verify exact hashes, complete hardware inventory, all node geometry/transforms/text, paint-only style changes, output hashes, alias identity and omitted unsupported IDs. Existing native schema/bindings and XML preservation checks pass.
- Extracted unchanged NanoSVG headers from the pin above; compiled `/tmp/eudora-native/raster` from `/tmp/eudora-raster.cpp`. **112 nonempty rasterizations** cover all 56 IDs at 230×106 and 115×53 aspect-fit envelopes. Evidence: `/tmp/eudora-native/results.json`, individual PNGs and visually inspected `/tmp/eudora-native/contact.png`. SNES clearly remains the supplied controller; no gross renderer failure observed. Source margins are preserved, not newly certified as unclipped.
- Maximum alpha per raster ranges 45–157 (0–255): antialiased thin details and source overlaps affect compositing. Intrinsic .45 works; not every pixel has uniform .45 alpha.
- Parent owns all-palette launch previews and full integration-suite evidence. Static compositions are illustrations, not ES screenshots. Without the archive/native probe, optional source-fidelity/expression checks explicitly skip. Python palette resolution is not the complete native theme loader.

## Local testing and remaining device checks

Borrowed-art redistribution rights remain unresolved; retain the source attribution and rights notice. For local testing, install both `gamesplash.xml` and `_inc/launch-hardware/` beside existing theme content, retain `colors.xml` and bundled fonts, and restart ES. Replace the old hardware directory rather than overlay-copying, to avoid leaving unsupported invented assets behind.

1. On stock Batocera 42 at 640×480, launch a game with marquee: confirm logo only, supplied controller/hardware art and selected palette.
2. Empty/stale marquee should show title instead; corrupt existing files require repair/removal. Unknown systems should show no hardware.
3. Launch from Favorites/all-games/groups to verify source routing; compare SNES controller, C64, handheld and unknown systems without inferring regional model detection.
4. Repeat palettes including Custom and independently check 320×240. Inspect faint details, title wrapping, wide/tall/padded marquees, overscan and physical 1702 readability.
5. Confirm no progress graphics, normal handoff/return, and unchanged startup/browsing screens. **Native frontend launch and physical CRT validation remain outstanding.**

Rollback: remove only candidate `gamesplash.xml` to restore built-in launch theme; the unused hardware directory can then be removed. Preserve startup `splash.xml` and unrelated files.

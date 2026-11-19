# Eudora launch hardware artwork — attribution and rights

These assets replace the earlier invented geometric drawings with the user's supplied **Eudora `controller.svg` artwork**. The source name is a role, not a guarantee of console chassis: **SNES is a controller**, C64 is a computer, handhelds depict the handheld itself. Source geometry, viewBoxes, dimensions, transforms, drawing order and metadata are preserved. No replacement consoles or unsupported-system drawings have been invented.

## Attribution and unresolved rights

`SOURCE-README.txt` is an unchanged copy of the supplied Eudora readme. Its credits state:

> All xml, all sounds, and some images created by AmadhiX.
>
> Based on the "Carbon" theme by Eric Hettervik, which is in turn based on "Simple" by Nils Bonenberger. Most system logos and line art images are borrowed from these themes.

The source readme separately licenses background textures and fonts; those notices do **not** establish the license of this line art. **Redistribution permission remains unresolved. This repository inclusion is not a license grant or clearance for further redistribution.** The enclosing theme's original-art CC-BY-NC-SA license is not being assigned to borrowed art. Product names identify systems, not endorsements.

## Exact provenance and coverage

`manifest.json` records the supplied ZIP name and SHA256, every exact archive-member source path and SHA256, every transformed asset SHA256, original viewBox, exclusions and aliases. Source archive: `doc_a34c2139f583_recalbox-themes-master-themes-eudora.zip`; members beneath `recalbox-themes-master-themes-eudora/themes/eudora/`.

52 hardware-system source files, plus four byte-identical aliases: `genesis → megadrive`, `sfc → snes`, `jaguar → atarijaguar`, `atarilynx → lynx` (56 runtime IDs). Arcade emulator/category sets `mame`, `fba`, `fbneo`, and nonhardware `doom`, `favorites`, `imageviewer`, `kodi`, `ports`, `scummvm`, `zmachine` are excluded. Source directories lacking `controller.svg` are not covered, including GC/Wii/PS2/PSP. Old fabricated 3DS/DS/Switch/Wii U/Vita and other unsupported drawings are removed. Unknown IDs have **no image**, never a generic fallback.

## Paint and rendering

Only explicit fill/stroke hex paints are normalized from source pale grays to white for native multiplicative palette tint. Root `opacity="0.45"` supplies intrinsic alpha; native Splash overwrites component opacity each frame. Source line work is largely **filled outline paths**, not newly assigned uniform strokes. Do not impose the old 200×100 canvas or 2.5-unit stroke contract. Pinned NanoSVG applies inherited opacity per shape, so overlapping shapes can exceed .45 composited alpha; browser group compositing may differ slightly. Thin source details are intentionally preserved and may be faint at 240p.

Native image geometry and bindings remain unchanged: aspect-fit maxSize `.36 .22`, center `.5 .73`, origin `.5 .5`, source-system path lookup. See `docs/qa/game-launch-screen.md` for verified native rasterization and remaining device checks.

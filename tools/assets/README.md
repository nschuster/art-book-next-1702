# Native trophy source font and scalable metadata outline

Latest metadata-only sizing correction: `sync.py:trophy_asset` now serializes the **exact U+F091 glyph outline** as SVG, extracted with FontTools `SVGPathPen`. Runtime has no FontTools dependency. The game-list glyph still uses the untouched native font/formatter; no font file is changed. The earlier text-resource description below documents provenance, not the current metadata rendering path.

Source glyph bounds are `(0,-128,1664,1408)`. The SVG uses square `viewBox="0 0 1664 1664"` and `translate(0 1472) scale(1 -1)` to flip font coordinates and center the full outline, without cropping, redrawing, or nonuniform scaling. The path is compared byte-for-byte with a fresh extraction by `previews/retroachievements-trophy-size-match/verify.py`. The generated document carries copyright, license URL and pinned provenance; the complete source-font OFL remains alongside this file. OFL's document-output exception applies to rendered glyph artwork.

See [new size evidence](../../docs/qa/ra-trophy-size-match.md).

`batocera42-fontawesome-webfont.ttf` is an **unchanged** copy of Batocera ES's embedded `resources/fontawesome-webfont.ttf`, used only by the static preview renderer. Runtime extras use the native resource `:/fontawesome-webfont.ttf`, so no font installation, emoji substitution or new runtime image asset is required.

- Source revision: `4adf26b43900d1a33887af6d8af3da2e99e398a5` (Batocera 42 ES).
- [Original font](https://github.com/batocera-linux/batocera-emulationstation/blob/4adf26b43900d1a33887af6d8af3da2e99e398a5/resources/fontawesome-webfont.ttf)
- SHA-256: `9e540a087924a6e64790149d735cac022640e4fa6bff6bd65f5e9f41529bf0b3`
- Embedded name-table version: `Version 4.3.0 2015`.
- Embedded copyright: **Copyright Dave Gandy 2015. All rights reserved.**
- License: **SIL Open Font License 1.1**, full text in [OFL-1.1.txt](OFL-1.1.txt). [Font Awesome 4.3.0 licensing declaration](https://github.com/FortAwesome/Font-Awesome/blob/v4.3.0/README.md#license).

## Exact native symbol evidence

[GameNameFormatter.cpp](https://github.com/batocera-linux/batocera-emulationstation/blob/4adf26b43900d1a33887af6d8af3da2e99e398a5/es-app/src/views/gamelist/GameNameFormatter.cpp#L16) defines `CHEEVOSICON` as `_U("\uF091")`; lines 213–214 append it after names when `mShowCheevosIcon && fd->hasCheevos()`. This is FontAwesome's trophy in the private-use area, **not Unicode U+1F3C6 trophy emoji**.

[Font.cpp](https://github.com/batocera-linux/batocera-emulationstation/blob/4adf26b43900d1a33887af6d8af3da2e99e398a5/es-core/src/resources/Font.cpp#L274) lines 274–292 list `:/fontawesome-webfont.ttf` first among fallback fonts; `getFaceForChar` (299 onward) selects the fallback when the game-name font lacks a glyph. Generated trophy text explicitly selects that same resource and U+F091. ThemeData.cpp PATH parsing accepts existing ResourceManager resources (1787–1796).

Preview rendering resolves this resource URI to the hash-verified local copy, preserving the same actual glyph. Pillow metrics/antialiasing remain an approximation of the native renderer; source identity is verified, but physical CRT rendering is not.

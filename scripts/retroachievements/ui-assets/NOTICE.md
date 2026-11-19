# Bundled UI bitmap font

font.bmp and widths.json are generated from this repository's `_inc/fonts/Roboto-Regular.ttf`, at 24 pixels, by `generate.py`. Copyright 2011 Google Inc. All Rights Reserved. Source font name table identifies Apache License 2.0; the full license is preserved in LICENSE-Roboto.txt. The bitmap is a derived raster atlas, not a modified font program.

Regeneration (development only): `python scripts/retroachievements/ui-assets/generate.py` (requires Pillow). Runtime requires neither Pillow nor the TTF: install font.bmp and widths.json beside progress_ui.py inside ui-assets/.

Supported atlas range: printable Latin-1. Labels normalize whitespace/control characters and replace unsupported glyphs with `?`. No network fetching or font discovery occurs at runtime.

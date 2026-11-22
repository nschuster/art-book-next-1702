# Retrorama comic logo artwork

These 56 logos are by **Filipe Bello (lipebello)**, from [Retrorama: Champion Edition](https://github.com/lipebello/es-theme-retrorama-ce), pinned at `afb1f4121c2de594349dba963d13b9d477cb2029` (`art/logo/*.png`). They are optional third-party artwork, not original Art Book Next artwork.

## Upstream notices

Upstream contains differing licence notices. They are preserved here without silently resolving them into broader permissions:

- `theme.xml` credits Filipe Bello and states **Creative Commons CC-BY-NC-SA**, without specifying a version (`UPSTREAM-theme.xml.txt`).
- Its README says **“Free to use, not for sale.”** (`UPSTREAM-README.md`).
- Its root `LICENSE` contains **GNU GPL version 3** (`UPSTREAM-LICENSE.txt`).

Retain the attribution and non-commercial/share-alike notice with these assets. No commercial permission is asserted. The theme's other licences do not replace these upstream notices. System names and trademarks remain with their respective owners.

## Processing and provenance

Only transparent outer padding is trimmed; the entire visible illustration is retained, proportionally fitted within 1024×512 pixels, and surrounded with a 2px transparent margin. Colours, aspect ratio, outlines and hand-drawn details are not redesigned. The PNGs are RGBA and are displayed without palette tint when selected. `manifest.json` records pinned source paths, original Git blob and SHA-256 hashes, source bounds, resulting dimensions and derivative hashes.

Rebuild from the repository root, with Python and Pillow installed:

```sh
python tools/import_comic_logos.py --output /tmp/retrorama-logo-rebuild
```

The importer verifies source SHA-256 before rendering and verifies derivative hashes. Use the Pillow version recorded in the manifest for byte-identical results. `--cache /path/to/originals` can use original upstream PNGs instead of downloading them. The default output is this asset directory. No preview or configuration files are written by the importer.

Coverage follows exact upstream system identifiers. Missing systems keep the theme's normal logo/text fallback rather than using an unrelated or regionally wrong wordmark. In particular, no Mega Drive wordmark is relabelled as Genesis. `auto-allgames.png` is upstream's Retrorama wordmark, retained as supplied.

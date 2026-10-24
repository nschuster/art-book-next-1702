# RetroAchievements progress on stock Batocera 42

Optional, local per-game theme extras; no replacement frontend, ROM edits, gamelist edits or polling daemon. The short-lived Python helper obtains validated counts from RA and writes private XML/SVG assets.

## Display (latest refined candidate)

Enable **Theme Configuration → Achievement Progress → On (sync helper required)**. Default is Off. Only Detailed, manual/dispatched automatic 4:3, metadata-enabled layouts are affected, with help on or off. All seven metadata fields and original media remain. Players stays beside Last Played at y=.70; Genre is at y=.76. RA Off retains the prior layout.

The separate bottom track spans x=.55–.95, starts y=.815 and has height **.045833333333333**, exactly the normal metadata value box height (not the older .055). It ends at y=.860833333333333, before the unchanged footer at .885416666666667. At 640×480 it is **256×22 pixels**; at 320×240, **128×11**. The count remains centered at (.75, .837916666666667), origin .5 .5, size .14 × .045833333333333. Only its fontSize changes: **.027777777777777**, a **16.67% reduction** from .033333333333333. The renderer's existing integer scaling yields **17px at 640×480 and 9px at 320×240**, versus 19px/10px previously; metadata stays unchanged. Sample `12/40` glyph width/height is 45.344×13px and 23.984×8px respectively, inside 90×22px / 45×11px count boxes. Native rasterization remains a device check.

Generated layers, in z-order:

1. `ra_progress_track` (99): solid white SVG, tinted natively by **`${gamelistListTextlistBackgroundColor}`**, exactly the current left sidebar background.
2. `ra_progress_bar` (100): separate transparent SVG containing only proportional unlocked/total rainbow fill. Smooth red→orange→yellow→green→blue spans the filled portion. White image tint preserves these colors. Zero progress/0 total leaves the fill transparent; completion fills the track.
3. `ra_progress` (101): native centered text, **`${gamelistListTextlistUnselectedColor}`**, the normal sidebar text color, not the selected accent or metadata color; font **`${themePath}/${fontBold}`**. Existing palette alpha is respected. No background badge, shadow, hardcoded white text or mismatched patch.

Both SVGs use `preserveAspectRatio="none"`, viewBox 0 0 1000 85.9375, and no border/stroke. Exact edge tests prevent transparent letterbox end strips and pale artifacts. Palette colors are not baked into shared assets: normal theme reload/reselection resolves the current palette without syncing/refetching. The font is anchored to themePath because bare relative font paths in an appended extra would otherwise resolve against the extras directory.

**Remaining contrast caveat:** C64 now uses opaque ivory `e9e1cc`, clearly readable on its empty dark track (10.74:1). Famicom uses its actual normal sidebar text `ffffff33` (20% white), so it is no longer identical to the track but remains faint (1.80:1). At full progress the yellow/green rainbow behind the count reduces full-coverage glyph contrast to about 1.29–1.61:1 for C64 and 1.11–1.17:1 for Famicom at 640×480. Anti-aliased edges can be weaker still. Default/SteamOS/OLED/Custom also inherit low-alpha normal sidebar text. No palette opacity change, badge or shadow was added: this preserves the approved design, not a claim of accessibility-level contrast. See `contrast-inspection.png` and `contrast.json` in the gallery for zero/sample/full evidence.

Counts use Hardcore or Softcore independently. Unmapped games have no generated progress; API failure never becomes a fabricated zero. Existing same-identity cached progress may remain offline.

## Install/configure

On Batocera, with this theme installed at `/userdata/themes/art-book-next-1702`:

```sh
python3 /userdata/themes/art-book-next-1702/scripts/retroachievements/install.py
python3 /userdata/themes/art-book-next-1702/scripts/retroachievements/configure.py
python3 /userdata/system/retroachievements/sync.py --config /userdata/system/retroachievements/config.json
```

Setup prompts for RA username and hidden **web API key**, not a password/token; defaults to Hardcore (`--mode softcore` is available). It discovers systems with gamelists and refuses to overwrite an existing configuration. Credentials stay local/private. After successful manual sync, optionally run `batocera-services enable ra-progress-sync`. The installer also supplies a targeted game-exit hook. Restart ES to load the updated theme, then enable the option.

**Upgrading an earlier candidate:** reinstall the helper and run a sync once to regenerate old XML/SVG geometry. Remove stale layout/color/font overrides from your private config's `template` (use `{}` for current defaults). Do not erase credentials. The shipped example and interactive setup now use empty templates. Subsequent palette changes need no sync. Reselect the game after refreshing progress; redraw of an already selected game is not guaranteed. Restart ES is a fallback, never forced during gameplay.

## Mapping and lifecycle safety

Extras are `/userdata/system/retroachievements/extras/<system>/<ROM stem>.xml`. Use positive gamelist `cheevosId` or verified explicit mapping; no title guessing/generic ROM MD5. Same-stem collisions within a system are rejected, including unmapped gamelist records. Cross-system collection routing is not supported.

Content-addressed SVGs use a separate checksum-backed `assets-manifest.json`, journaled before creation. Both track and fill are owned/referenced. Cleanup considers the full XML manifest, retains offline/untargeted references and removes only unchanged owned unreferenced files. Ordinary refreshes retain one common track plus one fill per active ratio, not every historical count. Unrelated/modified assets survive; modified XML defers cleanup. Account/mode/game-ID changes and removed mappings invalidate stale owned XML before network requests. Uninstall retains config/cache/extras/assets for reinstall; turn the theme option Off separately.

## Source and verification

Pinned Batocera 42 ES: `4adf26b43900d1a33887af6d8af3da2e99e398a5`.

- `DetailedContainer.cpp` appends per-game XML and rebuilds extras on game detail updates.
- `ThemeData.cpp` image schema supports pos/size/origin/path/color/zIndex/visible; the extra factory creates ImageComponent. Clone copies theme variables; appendFile preserves them, and property parsing resolves placeholders before COLOR/PATH handling. The themePath variable remains anchored to the theme, while currentPath changes for the appended file.
- Native text uses normal sidebar color and theme font bindings with supported alignment/origin properties. `MetaData.cpp` exposes cheevosId but not a native achievement-count field.

Full local tests cover real subprocess + loopback HTTP, mappings, identities, installation, asset ownership/cleanup, native XML bindings, exact proportional fill, palette pixels, geometry and count fit. Static previews rasterize the actual helper-generated SVG/XML, including native image color multiplication and RGBA text compositing—not a mocked palette effect.

Gallery: `previews/retroachievements-final-text/`, eight raw 640×480 images, external-label 640×535 versions, two contact sheets, and eight secondary 320×240 images. Primary: `commodore-64-480.png`. Custom explicitly uses the shipped template (= Default), not the user's device file. Values are fictional fixtures (12/40 plus 0/40 and 40/40 contrast checks), not account results. Regenerate with `python tools/render_ra_preview.py --all-palettes`, then `python tools/validate_ra_final_text.py`.

No native Batocera, live account/API, gameplay-refresh or physical CRT test was available. Static preview font centering is approximate, not proof of native baseline shaping or analog readability. See [QA](QA.md) and the [helper guide](../scripts/retroachievements/README.md).

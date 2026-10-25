# RetroAchievements progress on stock Batocera 42

**Latest metadata trophy size correction:** [exact-outline evidence and before/after previews](qa/ra-trophy-size-match.md). Supersedes the text-trophy box/slot discussion below: trophy ink is now 20×20 / 10×10 instead of 18×16 / 9×9. Its x=.548 optical placement keeps the approved 6px/3px gap without moving the bar or count. No game-list font, formatter, other metadata or palette changes.

Optional, local per-game theme extras; no replacement frontend, ROM edits, gamelist edits or polling daemon. The short-lived Python helper obtains validated counts from RA and writes private XML/SVG assets.

## Display (latest refined candidate)

Enable **Theme Configuration → Achievement Progress → On (sync helper required)**. Default is Off. Only Detailed, manual/dispatched automatic 4:3, metadata-enabled layouts are affected, with help on or off. All seven metadata fields and original media remain. Players stays beside Last Played at y=.70; Genre is at y=.76. RA Off retains the prior layout.

The combined native trophy + bottom bar stays within x=.55–.95. The trophy box begins at x=.55, width .03125 (20px at 640×480), followed by a .0078125 slot gap (5px). The track spans x=.5890625–.95, still starts y=.815 and retains height **.045833333333333**. It ends at y=.860833333333333, before the unchanged footer at .885416666666667. At 640×480 the bar is **231×22 pixels**; at 320×240 the static renderer rounds it to **116×11**, with a 10px trophy box and 2px raster slot gap. The visible trophy-ink gap is **6px/3px**, matching the main metadata rows; the bar begins one raster pixel left of the value slots to compensate for the trophy's inset ink. Native half-pixel rounding remains a device check. The count is centered in the resized bar at (.76953125, .837916666666667), origin .5 .5, size .14 × .045833333333333. Its fontSize remains **.027777777777777**, with existing static-preview scaling of **17px at 640×480 and 9px at 320×240**. Metadata, media, palettes and RA Off are unchanged. The trophy is generated in the same per-game XML as the bar, never as an unconditional theme element; no mapped/generated progress means no trophy beside the bar. Native rasterization remains a device check.

Generated layers, in z-order:

1. `ra_progress_track` (99): solid white SVG, tinted natively by **`${gamelistListTextlistBackgroundColor}`**, exactly the current left sidebar background.
2. `ra_progress_bar` (100): separate transparent SVG containing only proportional unlocked/total rainbow fill. Smooth red→orange→yellow→green→blue spans the filled portion. White image tint preserves these colors. Zero progress/0 total leaves the fill transparent; completion fills the track.
3. `ra_progress` (101): native centered text, **`${gamelistListTextlistUnselectedColor}`**, the normal sidebar text color, not the selected accent or metadata color; font **`${themePath}/${fontBold}`**. Existing palette alpha is respected. No background badge, shadow, hardcoded white text or mismatched patch.

4. `ra_progress_trophy` (101): SVG of the exact native U+F091 outline from the pinned `:/fontawesome-webfont.ttf`, in `${gamelistListMetadataIconColor}`. Only the metadata extra becomes an image; game-list glyphs/fonts are untouched. Square 20×20/10×10 image, x=.548, center y=.837916666666667. The full shape is uniformly scaled, not redrawn or stretched. See [latest sizing evidence](qa/ra-trophy-size-match.md).

Both SVGs use `preserveAspectRatio="none"`, viewBox 0 0 1000 85.9375, and no border/stroke. Exact edge tests prevent transparent letterbox end strips and pale artifacts. Palette colors are not baked into shared assets: normal theme reload/reselection resolves the current palette without syncing/refetching. The count font is anchored to themePath because bare relative font paths in an appended extra would otherwise resolve against the extras directory. The trophy instead uses ES's embedded resource.

**Remaining contrast caveat:** C64 now uses opaque ivory `e9e1cc`, clearly readable on its empty dark track (10.74:1). Famicom uses its actual normal sidebar text `ffffff33` (20% white), so it is no longer identical to the track but remains faint (1.80:1). At full progress the yellow/green rainbow behind the count reduces full-coverage glyph contrast to about 1.29–1.61:1 for C64 and 1.11–1.17:1 for Famicom at 640×480. Anti-aliased edges can be weaker still. Default/SteamOS/OLED/Custom also inherit low-alpha normal sidebar text. No palette opacity change, badge or shadow was added: this preserves the approved design, not a claim of accessibility-level contrast. See `contrast-inspection.png` and `contrast.json` in the gallery for zero/sample/full evidence.

Counts use Hardcore or Softcore independently. Unmapped games have no generated progress; API failure never becomes a fabricated zero. Existing same-identity cached progress may remain offline.

## Install/configure

On Batocera, with this theme installed at `/userdata/themes/art-book-next-1702`:

```sh
python3 /userdata/themes/art-book-next-1702/scripts/retroachievements/install.py
python3 /userdata/system/retroachievements/configure.py
python3 /userdata/system/retroachievements/sync.py --config /userdata/system/retroachievements/config.json
```

**No credential input is required.** Enable/sign into RA in Batocera's normal Game Settings first. Setup discovers systems with gamelists and writes only nonsensitive settings; it refuses to overwrite an existing configuration. Each sync reads Batocera's enabled state, username, login token and hardcore mode from `/userdata/system/batocera.conf`, ignoring passwords and never changing that file. Missing/expired token: reauthenticate in Batocera's RetroAchievements menu. The read-only client API uses HTTPS form POST, never credentials in URLs; both modes are cached. After successful manual sync, optionally run `batocera-services enable ra-progress-sync`. The installer also supplies a targeted game-exit hook. Restart ES to load the updated theme, then enable the option.

Old Web API configs remain supported; new manual setup is explicit (`configure.py --backend webapi`). To migrate, privately back up/move the existing config and rerun configure. Do not put the login token in an API-key field. Disabling RA or losing credentials removes unchanged owned extras on the next sync, not immediately: run sync and reload/reselect the game. Modified extras are preserved with an error directing you to restore them or disable the theme option. Same-account network/auth failures retain previously validated progress, never publish fake zeros.

**Upgrading an earlier candidate:** reinstall the helper and run a sync once to regenerate old XML/SVG geometry. Remove stale layout/color/font overrides from your private config's `template` (use `{}` for current defaults). Do not erase credentials. The shipped example and automatic setup use empty templates. Subsequent palette changes need no sync. Reselect the game after refreshing progress; redraw of an already selected game is not guaranteed. Restart ES is a fallback, never forced during gameplay.

## Mapping and lifecycle safety

Extras are `/userdata/system/retroachievements/extras/<system>/<ROM stem>.xml`. Use positive gamelist `cheevosId` or verified explicit mapping; no title guessing/generic ROM MD5. Same-stem groups within a system are **skipped in full**, including unmapped gamelist records and differences in extension, subdirectory or case; unambiguous games continue syncing. The warning reports only group/game counts, not private filenames or credentials. You do not need to rename the whole library: leave affected games skipped, or use distinct stems for those games and update their gamelist/mapping paths. Explicit IDs cannot make a shared output stem safe. Newly ambiguous groups lose unchanged helper-owned extras during full-mapping reconciliation, even on a targeted sync; unrelated/modified files are preserved (modified owned XML needing pruning causes an explicit error). Cross-system collection routing is not supported.

Content-addressed SVGs use a separate checksum-backed `assets-manifest.json`, journaled before creation. Both track and fill are owned/referenced. Cleanup considers the full XML manifest, retains offline/untargeted references and removes only unchanged owned unreferenced files. Ordinary refreshes retain one common track plus one fill per active ratio, not every historical count. Unrelated/modified assets survive; modified XML defers cleanup. Account/mode/game-ID changes and removed mappings invalidate stale owned XML before network requests. Uninstall retains config/cache/extras/assets for reinstall; turn the theme option Off separately.

## Source and verification

Pinned Batocera 42 ES: `4adf26b43900d1a33887af6d8af3da2e99e398a5`.

- `GameNameFormatter.cpp:16` defines `CHEEVOSICON` as U+F091; lines 213–214 append it after achievement-enabled game names. `Font.cpp:274–292` registers the embedded FontAwesome fallback. The preview uses a byte-identical copy of that exact pinned font; see [source, hash and license evidence](../tools/assets/README.md). This is not a Unicode trophy emoji or a lookalike SVG.

- `DetailedContainer.cpp` appends per-game XML and rebuilds extras on game detail updates.
- `ThemeData.cpp` image schema supports pos/size/origin/path/color/zIndex/visible; the extra factory creates ImageComponent. Clone copies theme variables; appendFile preserves them, and property parsing resolves placeholders before COLOR/PATH handling. The themePath variable remains anchored to the theme, while currentPath changes for the appended file.
- Native text uses normal sidebar color and theme font bindings with supported alignment/origin properties. `MetaData.cpp` exposes cheevosId but not a native achievement-count field.

Full local tests cover real subprocess + loopback HTTP, mappings, identities, installation, asset ownership/cleanup, native XML bindings, exact proportional fill, palette pixels, geometry and count fit. Static previews rasterize the actual helper-generated SVG/XML, including native image color multiplication and RGBA text compositing—not a mocked palette effect.

Trophy candidate gallery: `previews/retroachievements-native-trophy/`, eight raw 640×480 images, external-label 640×535 versions, two contact sheets, and eight secondary 320×240 images. Primary: `commodore-64-480.png`. Custom explicitly uses the shipped template (= Default), not the user's device file. Values are fictional 12/40 fixtures, not account results. Regenerate without overwriting earlier galleries: `PYTHONPATH=tools python -c "from render_ra_preview import render_gallery; render_gallery('previews/retroachievements-native-trophy')"`. The earlier `retroachievements-final-text/` gallery and contrast evidence predate the trophy/shortened bar and are retained unchanged as historical evidence.

No native Batocera, live account/API, gameplay-refresh or physical CRT test was available. Static preview font centering is approximate, not proof of native baseline shaping or analog readability. See [QA](QA.md) and the [helper guide](../scripts/retroachievements/README.md).

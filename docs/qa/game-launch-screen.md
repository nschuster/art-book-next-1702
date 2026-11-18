# Game launch screen QA

## Scope and contract

Only `gamesplash.xml` is new runtime content. Existing `theme.xml`, startup `splash.xml`, palettes, fonts, game-list/system geometry and menu settings are untouched. No new user option or helper. The native launch screen uses the selected palette's `gamelistListBackgroundColor` and `gamelistListDescriptionColor`, a centered aspect-fit **boxart**, and a single-line game title. Both native progress images are explicitly hidden; no extra artwork/progress animation is fabricated.

`colors.xml` is loaded first, then Custom's existing distribution-specific `theme-customizations/art-book-next/colors.xml`. Missing custom files retain the default palette; custom contrast is the user's responsibility. Local default-only subset declarations prevent an unset saved Color Scheme from activating every palette. They belong to the standalone launch parser, not the main configuration menu. They do not register new options in `theme.xml`.

## Pinned native source trace

Verified the existing clean `/tmp/ra-es-source` checkout at Batocera 42 ES **`4adf26b43900d1a33887af6d8af3da2e99e398a5`**. Tests read that exact object with `git show`, not whatever branch happens to be checked out. Source: [batocera-emulationstation at pin](https://github.com/batocera-linux/batocera-emulationstation/tree/4adf26b43900d1a33887af6d8af3da2e99e398a5).

- `es-app/src/FileData.cpp:748`: launch passes **`getImagePath()`**, `getName()` and the launched `FileData` into `setCustomSplashScreen`. The constructor's image is a scraped screenshot/image, **not necessarily box art**.
- `es-core/src/Window.cpp:935–945`: builds `Splash(..., false, bindable)`, then `update(customText)`. This supplies the game title after construction; a static label `<text>` is unnecessary and would be overwritten.
- `es-core/src/Splash.cpp:25–55`: chooses the theme root's **`gamesplash.xml`**, loads view **`splash`**, and initializes `imagePath` from that runtime image. A typed `<image name="background"><path>{game:thumbnail}</path>` overrides it because binding paths are explicitly accepted even before they exist. Merely adding a boxart extra would leave the unwanted built-in screenshot behind.
- `Splash.cpp:113–127,193–204`: applies image properties with PATH excluded, but common `GuiComponent::applyTheme` still records `_binding` expressions. The built-in background is explicitly made bindable and then updated from the launched game. `ThemeData.cpp:1777–1782`, `GuiComponent.cpp:899–901`, `BindingManager.cpp:203+`, and `ImageComponent.cpp:1126–1127` trace path binding into `setImage`.
- Use `{game:thumbnail}`, matching this theme's existing Boxart preset (`theme.xml:609`). Native FileData resolves it with `getThumbnailPath(false)` (thumbnail metadata/local thumb without image fallback). `{game:boxart}` is the separate **Alt BoxArt** field and would not reliably match the user's existing covers. Missing/broken thumbnail leaves the title without a screenshot fallback.
- `Splash.h:24` defaults percent to **-1**; `Splash.cpp:281` draws progress only for nonnegative values. Both progress image elements are also hidden explicitly.
- `ThemeData.cpp:1329–1378`: saved subsets are consulted, then local first entries. Without either, `ifSubset` accepts the node; local defaults avoid last-palette-wins on a fresh configuration. Launch lookup uses the `splash` system key, so use the global Color Scheme; per-console overrides are not promised.
- `ThemeData.cpp`'s actual `sElementMap` supports every emitted property. `maxSize` aspect-fits rather than crops; `roundCorners=0` removes the constructor's default rounded cover corners. `TextComponent.cpp` honors `multiLine=false` for native single-line truncation. `Font::getFromTheme` starts from `min(screen dimensions) × .05`; renderer scaling/rasterization still applies.

## Geometry (source-derived, not screenshots)

All normalized image/text coordinates use the screen, with no container/extras. The maximum cover envelope is x=.15–.85, y=.12–.72; actual artwork shrinks within it while preserving aspect ratio. The title is x=.08–.92, y=.79–.88. Essential content stays inside a nominal 5% margin; actual CRT overscan may differ.

| Framebuffer | Max cover | Title x/y, width/height | Nominal font before native scaling |
| --- | --- | --- | --- |
| 640×480 | 448×288 | 51.2/379.2, 537.6×43.2 | 24 px |
| 320×240 | 224×144 | 25.6/189.6, 268.8×21.6 | 12 px |

The file applies to all launch screens, with 4:3 as its review target. It does not change video timings, correct non-square pixels, force a minimum launch duration, or control emulator/boot screens. Long names truncate instead of wrapping/scrolling. Low-resolution readability and actual title glyph bounds need native/device inspection.

## Executed evidence

```sh
PYTHONDONTWRITEBYTECODE=1 BATOCERA_ES_SOURCE=/tmp/ra-es-source \
  python -m pytest tests/test_gamesplash.py -q -p no:cacheprovider
```

- **RED before runtime implementation:** `7 failed, 1 passed` because `gamesplash.xml` did not exist (including an explicit missing-entry assertion).
- **Second RED:** `1 failed, 8 passed` when local unset-subset defaults were absent; then added the local defaults and resolver fallback coverage.
- **GREEN:** `9 passed`, including all palettes, alpha-composited text contrast, custom include order and both distribution paths, missing-art binding behavior, portrait/landscape/square/very-wide aspect-fit geometry at both resolutions, typed native built-ins, every emitted property's native schema support, pinned launch bindings, and byte preservation of all pre-existing runtime XML against `2a93d44`.
- The schema test reads the actual upstream C++ map; the semantic resolver is Python. Neither executes the native XML parser or renderer. Without a checkout the source-contract test explicitly skips; set `BATOCERA_ES_SOURCE` to a Git checkout containing the pin to enable it.
- Initial full-suite run: `147 passed, 1 failed, 104 subtests passed`. The unrelated existing `test_system_playtime.py::test_opt_in_and_preservation` reapplied transforms to an already-updated `HEAD` baseline. The parent independently repaired that baseline test; this worker did not modify it. **Final full-suite rerun on the shared tree: `149 passed, 104 subtests passed`**, with pinned source checks enabled. `git diff --check` passed.

## Device acceptance still required

No native frontend, emulator launch or Commodore 1702 capture was run for this feature. On Batocera 42, install the standalone file beside `theme.xml`, restart ES, then:

1. At 640×480, launch games whose screenshot differs from box art. Confirm **only the cover**, correct title and palette; repeat in Default, Commodore 64, OLED, Light and Custom.
2. Try portrait, landscape, square and wide artwork; confirm no cropping/stretching/rounded clipping. Try no boxart and a broken path; title-only is expected, with no prior game's image.
3. Try long/localized names and 320×240. Inspect native ellipsis, title vertical clipping, composite readability and real overscan. Font/menu presets should not change the fixed launch typography.
4. Verify no progress bar, normal emulator handoff/return, and unchanged startup splash/game-list/system layouts. Very fast launches may make the transition barely visible; this theme adds no delay.

Rollback: remove only `gamesplash.xml` to restore the frontend's built-in launch theme. Do not delete the existing startup `splash.xml` or unrelated previews.

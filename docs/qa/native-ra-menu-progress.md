# Native RetroAchievements menu progress: stock Batocera limitation

## Verdict

**The requested palette-compatible native progress fill cannot be implemented in theme XML at the inspected Batocera 42 revision.** No runtime theme files were changed. All eight palettes, fonts, menu geometry, other menu colors and defaults remain as before. This investigation deliberately does not add an inert `menuProgress`, `progressColor`, `trackColor` or similar invented property.

This concerns the native RetroAchievements account overview and per-game achievement dialog, **not** the optional generated game-list progress bar and **not** the external Ports synchronization UI.

## Actual pinned source

Checkout inspected: `/tmp/ra-es-source`, Git HEAD
`4adf26b43900d1a33887af6d8af3da2e99e398a5`.

| Consumer / contract | Source evidence |
| --- | --- |
| Shared progress implementation | `es-app/src/guis/GuiRetroAchievements.cpp:43–107` |
| Empty track | line 89: `Renderer::drawRect(..., 0x00000032, 0x00000032)` (black with alpha 0x32) |
| Softcore fill | lines 93–96: literal `0x0B71C1FF` (blue), when softcore exceeds hardcore |
| Hardcore fill | lines 99–102: literal `0xCC9900FF` (gold/yellow), drawn after softcore |
| Label | line 48: `theme->TextSmall.font`, **`theme->Text.color`**, not TextSmall.color |
| `setColor` | lines 65–68: updates only `mText`; never a fill or track |
| Overview construction | line 203: `make_shared<RetroAchievementProgress>`; row color forwarding at 256–260 affects its label only |
| Game detail construction | `GuiGameAchievements.cpp:168`: same progress component |
| Game detail drawing | `GuiGameAchievements.cpp:196–216`: positioned/sized manually and rendered over the subtitle band |
| Component interface | `GuiRetroAchievements.h:23–38`: counters and label, no progress color properties or applyTheme override |
| Menu schema | `es-core/src/ThemeData.cpp:604–658`: supported menuText/menuTextSmall/menuGroup/background/icons/controls; no native RA fill/track property |
| Theme text consumer | `ThemeData.cpp:2432–2455`: menutext color/selection properties map to global Text theme fields |

Changing global menutext color would affect unrelated menus and the RA label, **but would leave the yellow fill untouched**. Changing selectorColor changes selection, not the manually drawn progress rectangles. Neither is an acceptable substitute for the requested scoped fix.

## Executed validation

```
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider tests/test_native_ra_progress_contract.py tests/test_menu_fonts.py -q
```

Result: **8 passed in 0.90s**. Four new tests characterize the pinned source limitation; four existing semantic/source tests verify menu font include resolution, Default behavior, and non-menu preservation. Source tests use `git show` at the exact pin, and explicitly skip if the upstream checkout is unavailable.

These passing tests do **not** assert that palette-aware native progress was implemented. No production edit was made, so no feature RED→GREEN repair is claimed. Runtime XML has no diff from this work; preservation across all eight palettes follows from leaving all runtime files unchanged, not from claiming a new palette binding exists.

`command -v emulationstation` returned no installed executable. No native GUI/component execution, custom ES build, device test, or new synthetic preview was performed. Source-backed evidence is sufficient to establish the literal-color consumer limitation, not visual CRT fit. Existing menu typography/summary overlap limitations remain unchanged.

## Options within the stated constraints

Keep stock native progress colors. Palette-compatible progress can be implemented independently in the already separate helper/Ports UI (another workstream); it does not recolor these native dialogs. Recoloring these exact fills would require a future upstream/native frontend change exposing and consuming theme colors, which is outside this task's stock-build authorization.

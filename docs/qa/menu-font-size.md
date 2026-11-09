# Independent menu font sizes — local candidate

Target: stock Batocera 42 ES `4adf26b43900d1a33887af6d8af3da2e99e398a5`, 640×480 Commodore 1702. No commit/push, frontend binary, helper or artwork changes.

## Exact options and scope

`menu-font-size`: `default` (Default), `large` (Large), `xlarge` (Extra Large). Default is first and makes no overrides: preserves every previous menu property and legacy general Font Size behavior. Large/Extra Large are fixed menu-only overrides independent of the general Font Size choice. Families, colors and all non-menu views are retained. Final `menu-font-size.xml` include wins over original menu definitions.

| Preset | title | footer | normal/group | small |
|---|---:|---:|---:|---:|
| Large | .0375 | .02916667 | .04166667 | .03333334 |
| Extra Large | .04166667 | .03333334 | .05 | .04166667 |

At 640×480 stock scale 1.31, native float32/int sizing gives title/footer/normal/small **23/18/26/20** and **26/20/31/26** pixels respectively. These are font raster sizes, not letter heights or a guarantee of full-string fit. A user-configured `MenuFontScale` overrides the automatic scale. Start with Large; Extra Large sacrifices visible row count. At 320×240 the engine uses a different scale; this is not a promise of comfortable 240p text.

## Source trace (all references at the pin above)

Repository: https://github.com/batocera-linux/batocera-emulationstation/tree/4adf26b43900d1a33887af6d8af3da2e99e398a5

- `es-core/src/ThemeData.cpp:604–623`: menuText, menuTextSmall and menuGroup schema includes fontSize. `2387–2465`: typed menu lookups map menutitle/menufooter/menutext/menutextsmall/menugroup to Title/Footer/Text/TextSmall/Group; Font::getFromTheme uses menu scaling.
- `es-core/src/resources/Font.cpp:90–96,1127–1151`: normalized size multiplied by smaller screen dimension, truncated, then menu-scaled. `es-core/src/renderers/Renderer.cpp:995–1012`: MenuFontScale override and stock 1.31 scaling at 480p.
- `es-app/src/guis/GuiRetroAchievements.cpp:44–50`: progress labels use TextSmall. `125–160`: game/console-name template references menu.text/menu.textsmall font variables. `193–226`: score text and row height use menu fonts. Constructor `284` onward derives from GuiSettings, with native MenuComponent header/subtitle.
- `es-core/src/components/CarouselComponent.cpp:1065–1069`: exports actual menu-font paths and sizes to the RA template. These sizes already include menu scaling; template TextComponent uses its own native theme/font path, so do not assume RA templated game-name glyph sizes equal the direct TextComponent sizes in the table. This inherited behavior is not corrected by this theme.
- `es-app/src/guis/GuiGameAchievements.cpp:49–94`: GameAchievementEntry title uses Text.font; description, points and unlock-date string uses TextSmall.font. Row height adapts to those font heights. `119` onward: dialog header and summary use GuiSettings/MenuComponent. `220–240`: progress area uses TextSmall metrics. No hardcoded FONT_SIZE font construction in either achievement-screen implementation.
- `es-core/src/components/MenuComponent.cpp:65,333–347`: title uses Title.font; subtitle uses TextSmall.font. `es-core/src/components/ButtonComponent.cpp:18–20`: buttons use Text.font. `es-core/src/guis/GuiMsgBox.cpp:87`: message/error text uses Text.font (its layout also uses a hardcoded large-font minimum height at line 138, not the message's font).

**Hardcoded limits:** RA windows use source WINDOW_WIDTH/height formulas (or full-screen mode), fixed image spacing and progress-column proportions; text size does not expose dialog width, wrapping or reserved-progress-area controls. The per-game screen is an achievement list, not a newly implemented expandable achievement-description dialog. Long strings may truncate; localized text and actual row/header/progress fit must be checked on the device. Emulator/RetroArch achievement popups are outside this frontend theme, and help prompts retain their own fonts. No claim that every Batocera screen obeys this control.

## Verification

Tests written before runtime XML: targeted run **3 failed, 1 passed**, including the real resolved normal-menu size failing with old `.03333333` versus requested `.04166667`. After implementation: **4 passed**. Added real include-graph/subset checks across general font settings and 4:3/manual/automatic-dispatched/16:9, default-menu comparison to upstream, non-menu preservation, supported type/property checks, and pinned runtime source checks (`BATOCERA_ES_SOURCE`, defaults to `/tmp/ra-es-source`). The source test skips explicitly if that checkout is unavailable; it passed here.

Strict existing whole-theme preservation tests allow only the exact new registration and final include via an explicit baseline transform. Existing RA queue and system-playtime implementation remains untouched; only the latter's preservation test is extended for the new registration.

Full-suite command: `python -m pytest tests -q`. First integration run: 139 passed, 1 failed (system-playtime preservation expected the old root tree); extended that guard with the exact registration/include transform, then reran the suite. Final rerun: **140 passed, 104 subtests passed in 50.79s** (exit 0). `git diff --check` clean.

## Device acceptance still required

1. Install theme.xml and menu-font-size.xml together; restart ES.
2. Compare Default against old appearance; select Large and reopen main RA list and a game's achievements.
3. Check long account/game names, three-line summary, progress labels, description/points/unlock dates, buttons and bottom help at 640×480.
4. Try Extra Large; inspect clipping and visible rows, scroll to last entry, test long localized strings and CRT overscan.
5. Change general Font Size while Large is active: menu sizes should remain fixed; gamelist retains its existing behavior. Restore Default to recover previous menu sizing.

No native GUI or CRT capture was available. Semantic/schema/source checks are not native rendering proof; no synthetic menu screenshot is presented as one.

# Palette-aware achievement companion screens

Approved palette-aware companion update. No Batocera device installation or
physical-display validation was performed.

## Implemented

The SDL progress and Ports setup windows read the active Art Book colour scheme
at launch. Background, text, divider, track and fill come from the installed
palette. Current `subset.color-scheme` in `es_settings.cfg` wins; the CR-separated
`themesettings/<ThemeSet>.cfg` is only a fallback when the current value is absent.
Pinned ES `4adf26b43900d1a33887af6d8af3da2e99e398a5` saves that per-theme snapshot
when switching away (GuiMenu.cpp:3760–3786); Settings.cpp:425–456 persists current
string settings. Theme folder lookup follows native last-found precedence.

Custom reads the existing theme-customizations/art-book-next/colors.xml. Bounded
local XML, simple aliases and alpha colours are supported; arbitrary third-party
expressions/includes are not. Missing/malformed sources use the prior readable
companion fallback. No credentials/settings are changed. Reopen after switching
palette. Menu surfaces are intentional: OLED's menu is #111111, not its black
browsing background. Light retains its dark menu; its black list accent falls
back to palette text for visible progress. The tiny header rainbow is unchanged.

A white bitmap atlas enables SDL texture tinting without changing typography or
adding runtime packages. Installer and standalone bootstrap include ui_palette.py.
Update theme/helper via the existing Ports install/update action; no progress
regeneration or full sync is required for these UI colours.

## Verification

- Initial worker tests observed four failures before implementation.
- Independent review found stale-snapshot precedence and Light fill contrast
  defects. Two parent regression tests reproduced both failures before correction.
- Palette tests after correction: **6 passed**.
- Final complete suite with native probes: **330 passed, 1 skipped, 104 subtests
  passed**, 93.19 seconds. `git diff --check` and bootstrap `sh -n` passed.
- Actual installed SDL dummy-driver captures: all eight registered palettes at
  640×480 and independently at 320×240 (16 frames). Current selections deliberately
  override a stale C64 snapshot. Custom uses the shipped template, not user data.
- Executed the actual self-extracting standalone Ports bootstrap against a local
  fixture and captured its C64 setup screen. No installation action was triggered
  by that screenshot; installation/lifecycle regressions are covered separately.
- Final Light, C64 sync and C64 setup frames inspected for visible fill and text
  bounds. Primary gallery: `previews/ra-sync-palettes/`; data are synthetic.
- No theme XML, game-list rainbow bar, metadata or worker lifecycle changes.

The native menu's hardcoded gold/blue progress is a separate stock limitation:
see [native-ra-menu-progress.md](native-ra-menu-progress.md). It has not been
recoloured. SDL fixture captures are not native ES or physical CRT validation.

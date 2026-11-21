# Native controller status — local candidate

No commit, push, install or device restart was performed. Base: `a22c581b08e55ec34d4cb061f44bb6ccd4ef24cb`; inspected stock Batocera 42 ES: `4adf26b43900d1a33887af6d8af3da2e99e398a5` in `/tmp/ra-es-source`.

## Scope / operation

- Theme Configuration → **Controller Status Icons → On / Off**, default **On** (`controller-status:on` first registration).
- A final `controller-status.xml` include overrides the old hidden screen component. Only `screen/controllerActivity` changes; no fake extra image is added to any game/system view. New original SVG is a texture for detected pads, not a connected-device assertion.
- Position `.03125 .041666666666667`; size `.4 .041666666666667`; left alignment; spacing `.00625` of screen width. 640×480: first slot 20,20, 20×20, gap 4. 320×240: first slot 10,10, 10×10, gap 2. Fixed independent of Font Size, matching Default header height.
- Normal tint follows `${systemIndicatorColor}`. Native activity/hotkey colors retained. Native wheels/guns retain engine fallback shapes (no new themed wheel/gun images).
- Existing clock/network stack, other native screen components, metadata/media/layouts/colors/fonts/RA scripts and overlays untouched. Theme registration/include is the sole change to `theme.xml`.

## Native contract

Pinned source anchors:

- `ControllerActivityComponent.cpp:185–235,296–339`: visibility gate, `ShowControllerActivity`, `lastKnownPlayersDeviceIndexes`, absent/invalid pad skipped; native battery-level availability and flashes. No paired-only Bluetooth query.
- `InputManager.cpp:1088–1105`: clears/rebuilds player-device map from actual player configs; maps device index, battery level, wheel flag. Calls at 439,493,1284.
- `ControllerActivityComponent.cpp:387–487`: consumes imagePath, color, itemSpacing and left alignment; spacing multiplies screen width. Native width is not a clipping boundary; optional battery labels can extend the row.
- `ThemeData.cpp:430–459`: supported controllerActivity schema; no theme-level override of global setting.
- `Window.cpp:743–744,1292`: window renders this component only with global activity enabled, applies screen/controllerActivity theme. It suppresses the component behind menus on small screens.
- `Settings.cpp:21,150`: **ShowControllerActivity**, default true.
- `GuiControllersSettings.cpp:15–30,155–185`: Batocera Linux label **CONTROLLER & BLUETOOTH SETTINGS**, group **DISPLAY OPTIONS**, **SHOW CONTROLLER ACTIVITY**, optional **SHOW CONTROLLER BATTERY LEVEL** (`ShowControllerBattery`). Main-menu entry: `GuiMenu.cpp:162`.

User path: **Main Menu → Controller & Bluetooth Settings → Display Options → Show Controller Activity → On**. This and the theme On setting must both permit display. Theme Off hides it regardless of global On. Global Off remains authoritative. For icons only, turn native battery-level display Off; no theme setting is invented for that global option.

## Tests / evidence

`tests/test_controller_status.py` resolves all 11 registered ratio selections, On/Off, help states and all general font presets. Checks system/basic/detailed/menu with metadata variants and RA On/Off unchanged, screen-component isolation, geometry at both CRT resolutions, exact native schema/runtime contract, and exact ordered-tree preservation versus the pre-feature commit. Existing strict palette/RA/system-playtime guards gained only the exact registration/include transformation. Resolver dispatch selection is not a test of native ratio detection or live devices.

RED before production XML: `/tmp/controller-status-red.log`: 14 failed / 11 passed (hidden controller component, missing registration/geometry/include).
Targeted GREEN including strict guards: 36 passed.

Final full suite: **241 passed, 1 skipped, 104 subtests passed in 73.72s**, exit 0. Sole skip is the unavailable supplied Eudora archive for an unrelated game-launch source-fidelity check. Available native SVG and launch-expression probes ran. Command:

```sh
BATOCERA_ES_SOURCE=/tmp/ra-es-source BATOCERA_SVG_RASTER=/tmp/game-launch-nanosvg BATOCERA_LAUNCH_EXPR_PROBE=/tmp/launch-expression-probe/launch-probe python -m pytest tests -q -rs
```

Full log: `/tmp/controller-status-full-suite.log`; handoff: `/tmp/controller-status-theme-result.md`. `git -c core.whitespace=cr-at-eol diff --check` passed. The first full run exposed an older game-launch theme byte guard; it now permits only the exact controller registration/include transformation, retaining every other XML byte guard.

Pinned NanoSVG asset check at 20×20 and 10×10 is an actual SVG rasterization, not a native controller component render. Asset-only outputs: `/tmp/controller-status-icon-check/`. The existing static renderer resolves only detailed-view components and does not render native screen controller activity faithfully, so no invented connected-controller screenshot is supplied. An asset inspection is not a representative system/detailed preview or evidence of detected hardware.

## Device verification / deployment

Update `theme.xml`, `controller-status.xml`, `_inc/images/controller-status.svg` together under the actual active `/userdata/themes/art-book-next-1702-master/` folder. No RA reinstall/configuration/resync is necessary. Reload the theme; if an SSH restart is needed, `batocera-es-swissknife --restart` force-restarts ES and may lose unsaved changes—only use with no game running.

Check On/Off, global gate, zero/one/two detected controllers, unplug/reconnect, activity/hotkey, optional battery, system and detailed browsing, current palette, help on/off, 640×480 and 320×240. Confirm top/left CRT overscan and multi-controller row clearance. No headphone feature, frontend patch, device overlay, new helper or publication.

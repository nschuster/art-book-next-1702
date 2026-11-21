# Independent Ports feature actions

Candidate implementation; not installed on a physical Batocera device.

## User-visible contract

Seven entries: Install Features; Enable Achievements Sync; Disable Achievements Sync;
Enable Playtime Sync; Disable Playtime Sync; Refresh Achievement Progress;
Refresh Saved Playtime. Each has an individual confirmation/feedback screen and
Ports gamelist name/description/Utilities genre/project attribution. The native
4:3 theme does not display descriptions in its metadata panel, so operation text
also appears on launch.

Fresh installation does not enable either background feature. Upgrades preserve
existing enabled/disabled state. Installation is not a full-library sync. Manual
refresh does not change either automatic-sync setting. Disabling retains saved
login, cached achievement progress and generated playtime totals. Achievements
and playtime are independent; only achievements need the saved RA login/network.
The achievement disable action suppresses both after-game and optional startup
work, without changing unrelated Batocera service settings.

Every action screen displays live checkbox-style indicators for both automatic
sync settings: `[x]` enabled, `[ ]` disabled or not installed, and `[?]` unavailable
when state cannot safely be read. These are read-only indicators; use the separate
Enable/Disable actions to change settings. They show configured automatic sync,
not worker activity, credential validity or the result of the latest refresh.
They are not native checkboxes in Batocera's Ports list. Viewing status makes no
configuration changes. Descriptions use measured font widths rather than a
character-count cutoff.

Playtime files refresh after a compatible saved metadata update; the display still
requires a theme reload. No forced frontend reload, native menu modification,
custom frontend installation or display-output changes.

## Delivery

Copy the generated standalone installer to `/userdata/roms/ports/`, replacing the
previous copy. Launch and confirm installation, then use native Update Gamelists
to discover the individual entries. Replace an older copied bootstrap for this
upgrade. The new installed Install Features action can use updated local theme
sources for subsequent helper upgrades; its self-contained copy is the fallback.
The initial bootstrap may be removed manually after successful installation;
Install Features remains available. Existing legacy Ports entries are not deleted
without ownership verification.

The embedded payload is built from an explicit source allowlist, including the
license-covered UI fonts and example configuration, never private config/cache.
Scripts quote filesystem paths and use the selected data root. The install path
and generated individual entries are tested with a temporary root containing
spaces. Existing non-feature gamelist entries/comments and edited descriptions
must survive reinstall.

## Verification gate

- Regression tests for default disabled state, explicit independent toggles,
  manual refresh while disabled, and saved-state preservation.
- Run the real extracted standalone installer, then its generated action shells.
- Verify newly enabled achievements have a saved-login backend configuration.
- Verify installed helper/source bootstrap consistency and repeat installation.
- Inspect actual SDL action screens for clipping at 640x480.
- Run the complete stable-candidate suite after rebuilding the embedded payload.

See `controller-overlay.md` for the separate controller colour/font-size checks.
Physical CRT rendering and controller/device behaviour remain unverified.

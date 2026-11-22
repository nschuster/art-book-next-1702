# Art Book Next 1702 — conservative 4:3 Batocera fork

Maintained as **[nschuster/art-book-next-1702](https://github.com/nschuster/art-book-next-1702)**. Based on **Anthony Caccese's [Art Book Next](https://github.com/anthonycaccese/art-book-next-es)**; original artwork, fonts, credits and CC-BY-NC-SA 2.0 licensing are retained below.

## What this fork changes

The 4:3 layout keeps the original media geometry and replaces the description with icon-based metadata.

The layout change is confined to `aspect-ratio-4-3.xml`; an optional **Commodore 64** palette is registered in `theme.xml` and defined in `colors.xml`. In Detailed view, manual 4:3 and Automatic when dispatched to 4:3 replace the description with **seven metadata fields**: release date, rating, players, genre, play time, play count and last played. Developer and publisher are omitted.

- **Default**, **Release Date & Play Time**, and **Play Time & Play Count** all display the same complete panel, with help on or off. Existing option names remain for compatibility; they still select the original pairs at other ratios.
- **Off** is unchanged (no description or metadata).
- Original theme SVG metadata icons and rating stars accompany native typed values, rather than a label/value table. Both dates use full `YYYY-MM-DD`.
- Play time now shows **total hours and minutes** (`49h 15m`, never days; unplayed: `0h 0m`) in the same icon/value position. Stock Batocera 42 supplies raw seconds to a bound text extra; no helper, gamelist edit or new setting is needed, and Achievement Progress can remain Off. The parser uses floats: minute rounding can be off at very large totals (observed around 4,660 hours). This accepted limitation does not change recorded playtime. Other ratios retain their original formatter.

For this playtime update, only `aspect-ratio-4-3.xml` needs replacing on an existing installation; restart EmulationStation afterward. No RA reinstall, configuration or resync is needed. This candidate is verified by the pinned parser and static previews, not yet on the device.

Image/video size, position, cropping and marquee geometry are **identical to upstream** for each artwork mode and help setting. The original list, fonts, system selection, Basic view and help-footer geometry remain; original colors remain unless the optional palette is selected. The metadata uses upstream icons, Roboto Bold and metadata colors in five compact rows beneath the original-size media. Font size is fixed across font presets; long text values use native single-line ellipsis. Other aspect ratios are unchanged.

## Optional comic system logos

Select **User Interface Settings → Theme Configuration → System Logos → Comic (Retrorama)**. **Default** and **Custom** remain available, and the default selection is unchanged. The 56 genuine Retrorama logos retain their original colours rather than taking the selected palette's tint. They apply to the large system logo, Canvas overview, Custom Full Screen logo carousel and Basic/Detailed game-list headers. Small hardware/carousel icons and game marquees are unchanged.

Coverage follows Retrorama's exact system identifiers. A missing comic PNG falls back to the existing Art Book logo with its normal palette colour; the existing text fallback remains available when neither logo exists. C64, for example, keeps its original logo. This does not change loading screens, display timing, metadata or saved settings.

For an existing installation, merge the comic update into **`/userdata/themes/art-book-next-1702/`**, replacing `theme.xml` and `console-showcase.xml` and adding `_inc/systems/logos-comic/`; do not delete other theme files. Reload the theme, then select the new option. No Ports/RA setup or resync is required.

Artwork: **Filipe Bello (lipebello), Retrorama: Champion Edition**. Pinned sources, hashes, processing and retained upstream licensing notices are in [the asset attribution](./_inc/systems/logos-comic/ATTRIBUTION.md). Upstream states non-commercial/share-alike and “not for sale”; no commercial permission is claimed. See [Comic logo QA](docs/qa/comic-logos.md) for test coverage and device-validation limits.

## Optional Canvas console carousel (local candidate)

**Console Hardware & Info → On (Canvas hardware)** replaces only the system-selection presentation with the original Art Book logo above Canvas hardware in a left column. The right column contains **values only**: hardware type, release year, architecture, CPU, RAM and market-labelled launch price—no repeated manufacturer/name or field headings. Verified-data coverage is partial; unsupported values remain `Unknown`. **Off is the default** and preserves the previous presentation, including Custom Full Screen. Game lists, launch screens, controller status and achievement panels are unchanged. Source metadata is inherited, not newly historically certified; missing artwork has a text fallback.

The left-column refinement anchors both images at 7% of screen width, preserving aspect ratio and original logo bytes. Hardware was already alpha-cropped during import; intrinsic transparency in some original/custom SVG logos can still indent their visible ink. The C64 review fixture has matching visible left edges at both resolutions. This is not permission to crop or replace all host logos.

[All eight palette previews](previews/canvas-carousel-left-palettes/README.md) include readable 2×2 sheets, individual **640×480** frames and independently composed **320×240** frames, with identical C64 artwork. **Custom means the shipped template**, not private device settings. Default/Light/OLED/Custom share much of their system-view styling; their game-list differences are not invented here. These are labeled static approximations, not native frontend or CRT captures. The initial `previews/canvas-carousel/` gallery is retained unchanged.

**Not committed, pushed or installed.** Canvas's source-license/README rights conflict remains unresolved; implementation and preview approval do not establish redistribution clearance. See [left-column QA](docs/qa/canvas-left-palettes.md) and `_inc/canvas-hardware/manifest.json` for evidence/provenance.

## Controller status icons

**Local candidate, not yet published or device-tested.** Select **User Interface Settings → Theme Configuration → Controller Status Icons → On / Off**. **On is the default**. Actual player controllers detected by EmulationStation appear at the **top left**, opposite the unchanged clock/network group. With no detected player controller, no gamepad icon is drawn. This uses the native `screen/controllerActivity` component—not permanent decorative icons, polling scripts or an emulator overlay. It applies across aspect ratios and keeps the existing metadata, media, palettes and achievement panel intact.

Batocera's global setting must also be enabled: **Main Menu → Controller & Bluetooth Settings → Display Options → Show Controller Activity → On** (`ShowControllerActivity`, native default true). The theme option cannot override that global switch. **Show Controller Battery Level** in the same section adds battery text only when the device reports a level. Battery text now matches the clock's nominal font size for each font preset. Stock Batocera couples that text size to the icon height, so the controller icons grow too; the first anchor and clock stay unchanged. Battery uses the native regular font while the clock is bold, so their glyph shapes are not identical. Input and hotkey feedback use the selected palette's menu accent rather than the native pink/blue defaults.

At **640×480**, the first slot still starts at **20,20**, with **4px** spacing; at **320×240**, these become **10,10** and **2px**. Native `tinyScreen` conditions select the correct battery scaling, including the frontend's small-screen override. The row does not clip or wrap: many battery-bearing controllers can still overlap right-side indicators. Two battery-bearing controllers are covered by conservative layout checks; unusual FontScale settings and physical CRT readability need on-device checking.

Update **`controller-status.xml`** in **`/userdata/themes/art-book-next-1702/`**, retaining the existing `theme.xml` include and `_inc/images/controller-status.svg`. Reload the theme; no RA reinstall/resync is needed for the controller appearance. Source/schema and resolved-theme tests are not a native GUI capture. See [controller overlay QA](docs/qa/controller-overlay.md).

## Optional system total playtime (hours and minutes)

Enable **Theme Configuration → System Playtime → On**. **Off is the default**; **System Count** remains independent. The selected-system total appears below the unchanged count, without moving original artwork or logos.

The display uses **total hours and minutes**, for example `51h 4m`, with `0h 0m` for a refreshed unplayed system. Stock Batocera 42 exposes only a preformatted system timecode, unlike the individual-game raw-seconds binding. A small **independent local helper** therefore generates these totals using integer arithmetic from saved gamelists. It does not use RetroAchievements credentials or make network requests. Missing generated totals show `Playtime unavailable`, never an invented zero.

**Snapshot limitation:** totals cover saved games in each mapped gamelist, not the native visible-game/filter aggregate. The Ports refresh also reads compatible saved EmulationStation recovery records, replacing the matching game's old value rather than counting it twice. Collections/custom paths require correct native system and ROM-path mapping. The helper never alters gamelists or recovery records.

**Optional automatic background updates:** use **Ports → Enable Playtime Sync** after installing the features. Installation and manual refresh do not enable it. Use **Refresh Saved Playtime** for an immediate local refresh, or **Disable Playtime Sync** to retain the totals while suppressing automatic updates. After a game exits, a detached, bounded worker waits for Batocera to save that game's updated metadata, then refreshes only the affected system. It does not require RetroAchievements, scan every system after each game, contact a server, or restart/reload the frontend. If saving is disabled, no eligible fresh save appears, or validation fails, it leaves existing totals unchanged rather than estimating time.

**The displayed number still updates only when the theme reloads.** Returning to the carousel or reselecting a system does not reload its XML include. Toggle **System Playtime Off → On** to display the latest generated snapshot. This background-only behavior deliberately avoids disruptive full-library reloads. The independent game-detail playtime field continues to use native live metadata.

The worker requires an existing saved base gamelist and a compatible, unambiguous recovery record (or freshly saved base). Recovery-only systems without a base remain unsupported. Invalid or duplicate records fail closed; the last valid total is retained. Each exit worker waits at most 120 seconds, then stops. There is no perpetual polling service or automatic startup scan.

For diagnostics, `/userdata/system/configs/art-book-next-system-playtime/.last-result.json` records the last completed CLI refresh as `updated` or `not-refreshed`, a system count and completion time, without game names, paths or credentials. This is not proof that the currently displayed theme has reloaded. Manual refresh and automatic enable are separate actions: a failed refresh does not change your enable setting.

Use **Ports → Disable Playtime Sync** to disable background updates without removing helpers or saved totals. **Refresh Saved Playtime** remains available while automatic updates are disabled.

All ratios share the existing count geometry. The line stays centered at `.5 .85`, height `.05`, below the count at `.5 .78` and above the help footer. Font presets are retained. Primary review is 640×480 with an independent 320×240 check; physical CRT readability remains unverified. Update `system-playtime.xml` together with the helper sources; this does not change individual-game playtime or require an achievement resync.

## Optional menu font size

Select **Theme Configuration → Menu Font Size → Default / Large / Extra Large**. Start with **Default** when using achievement review: device photos confirmed summary/progress overlap with larger fonts in the stock frontend. This affects stock Batocera 42 menus, including the RetroAchievements account/game list and the selected game's achievement titles, descriptions, points, unlock dates and progress text. It needs **no helper, RA resync or custom frontend**.

- **Default** preserves the previous menu appearance exactly, including its existing response to the general **Font Size** setting.
- **Large** and **Extra Large** override menu typography independently of that general setting; game-list, metadata, system, artwork and help-prompt fonts are untouched. Menu font families/colors are retained.
- These are global menu presets, not RA-only controls. At 640×480 with stock menu scaling, normal/small font raster sizes are approximately **26/20 px** (Large) and **31/26 px** (Extra Large); these are font sizes, not measured letter heights. RA game-name template scaling can differ.
- Larger text means fewer visible rows. Native fixed-width progress areas, long game names/descriptions, translations and CRT overscan can still clip; this does not add wrapping or resize the native dialogs. It does not change emulator achievement popups or in-game RetroArch menus.

These presets are source/semantic-tested, not device-tested. Update the complete theme (including both new XML includes), restart EmulationStation, then select the option and reopen the menus. Static previews also indicate possible summary/progress overlap at larger sizes; verify on the device. See [menu font QA and exact source evidence](docs/qa/menu-font-size.md).

## Independent Ports controls and sync status

Install Features adds separate Enable/Disable entries for achievements and
playtime, plus Refresh Achievement Progress and Refresh Saved Playtime. Each
screen shows live checkbox-style **automatic sync** status for both features:
`[x] Enabled`, `[ ] Disabled` or `Not installed`, and `[?] Unavailable` if state
cannot safely be read. These indicators are read-only; change settings with the
separate actions. They are inside the helper screen, not native Ports-list
checkboxes, and do not claim a worker is running or the latest refresh succeeded.
Opening a screen never enables sync. Installation preserves upgrade settings;
fresh installs start disabled. See [Ports controls](docs/qa/ports-actions.md).

## Optional sync launcher with live progress

The optional helper installer flag **`--ports-menu`** adds **Ports → Refresh
RetroAchievements Progress**. It opens a separate controller-friendly screen
showing the current console/game, work counts, a progress bar and retry/result
status. Closing the screen returns to browsing while synchronization continues;
reopening during a run attaches without restarting it. This is a stock-compatible
Ports application, not a new native Main Menu item or ScreenScraper dialog.

The sync and feature-setup screens read the active **ThemeSet / Color Scheme**
when opened, using the installed Art Book palette for the background, text,
separator, progress track and fill. This includes Custom's existing
`/userdata/theme-customizations/art-book-next/colors.xml`; the adapter supports
this fork's colour-variable format, not arbitrary third-party theme expressions.
Missing or malformed settings/palettes use a safe readable fallback. No settings
or credentials are changed. After changing colours, close and reopen the screen.
To update an already-installed sync screen, update the theme files and run
**Ports → Install Art Book Next Features → A** once; no full-library resync is
needed for this appearance change. The game-list rainbow bar is unchanged.

**Native achievement-menu bar:** stock Batocera 42 hardcodes blue Softcore and
gold/yellow Hardcore progress. Theme XML controls the label/font, not those bar
colours. The companion screen's palette support does not recolour that native
bar or change achievement mode. A native bar recolour would require frontend
support; this fork does not install a custom frontend. See the
[source-backed limitation](docs/qa/native-ra-menu-progress.md).

Existing login/configuration is reused. No custom frontend, pip packages, or ROM
hashing is involved. It refreshes safely mapped achievement-enabled games; the
work count refers to unique RA game IDs, not every ROM. See the
[helper installation and controls](scripts/retroachievements/README.md#optional-controller-driven-full-library-sync)
and [verification/device checklist](docs/qa/ra-ports-progress.md).

## Game launch screen

Game launches use a standalone **`gamesplash.xml`**: a large aspect-fit **selected-game logo (marquee)**, subdued **Eudora system line art** underneath (controllers, handhelds or computers, depending on the source asset), and the current palette's background. The game title replaces the logo **only when its path is empty or missing**. A static palette-coloured **LOADING…** label sits below the artwork; it is an activity message, not measured progress. No cover, console wordmark, loading/progress graphics or new theme setting. Existing startup `splash.xml`, game-list/system layouts and artwork settings are unchanged.

Install **both `gamesplash.xml` and `_inc/launch-hardware/`** in the installed fork (beside the existing `theme.xml`, retaining `colors.xml` and `_inc/fonts/Roboto-Bold.ttf`), then restart EmulationStation. It follows **Color Scheme**, including Custom's existing `/userdata/theme-customizations/art-book-next/colors.xml`. The local candidate replaces the authored drawings with source-preserving Eudora artwork from the supplied archive; unlisted systems show no hardware rather than an invented substitute. Attribution and the unresolved line-art redistribution license are recorded with the assets; inclusion in this repository does not establish redistribution permission. [Exact coverage and source verification](docs/qa/game-launch-screen.md). Existing but corrupt logo files cannot trigger the filesystem-based title fallback; repair/remove the bad scraped image. Long fallback titles wrap within a fixed box. This is an ES launch transition, not an emulator overlay or boot video; its duration is controlled by the frontend.

Primary target: **640×480 physical 4:3**, secondary **320×240**. This revised candidate has passed pinned Batocera 42 source/schema, expression-evaluator and native SVG rasterization checks; actual launch rendering and CRT readability still require device QA. No optional RA helper is needed.

## Install on Batocera

Keep the original theme installed for easy comparison/rollback. Install this fork into its **own** folder; do not overwrite `art-book-next`.

### Controller-friendly feature setup (no repeated SSH)

With this updated theme installed, copy **[`Install Art Book Next Features.sh`](scripts/retroachievements/Install%20Art%20Book%20Next%20Features.sh)** to `\\BATOCERA\share\roms\ports\`, replacing an older bootstrap if present. Update game lists, launch it and confirm **A / Enter**. Then run native **Update Gamelists** again to discover these independent entries:

| Ports entry | Action |
| --- | --- |
| **Install Features** | Install/update local helpers and Ports entries; preserve existing sync settings. Fresh installations start disabled. |
| **Enable Achievements Sync** | Enable after-game achievement updates; reuse saved Batocera login. |
| **Disable Achievements Sync** | Suppress after-game and optional startup updates; retain login and cached progress. |
| **Enable Playtime Sync** | Enable local saved-playtime updates after games, independently of achievements. |
| **Disable Playtime Sync** | Suppress automatic playtime updates; retain existing totals. |
| **Refresh Achievement Progress** | Open the manual progress screen, including while automatic syncing is disabled. |
| **Refresh Saved Playtime** | Refresh saved totals without changing automatic-sync settings. Reload the theme to display them. |

Each entry has a name, description, Utilities genre and project attribution in the Ports gamelist. Existing unrelated entries and edited metadata are preserved. Each action has its own controller-friendly confirmation/feedback screen; **B / Back / Esc** exits. No all-in-one menu is required. The theme's 4:3 metadata layout may not show game descriptions, so the action screen also explains the operation.

The self-contained bootstrap embeds the installers, helpers, UI and license-covered fonts from this update. It never downloads code and does **not** install/update the theme itself. Recopy it when upgrading this delivery. After setup, the original bootstrap can be removed manually; the installed **Install Features** entry handles reinstalls of its installed version. To upgrade to a newer release, use that release's bootstrap. No credentials or user state are bundled. The legacy setup CLI remains available for compatibility, but is not the primary Ports workflow.

### Advanced alternative: SSH installation (no Git required)

Run these blocks in an **SSH terminal connected to Batocera**, not on your PC. First enable/sign into RetroAchievements in Batocera's normal settings if you want the progress bar. These commands do not ask for credentials.

**1. Download/install or update the theme.** The download is extracted and checked first. An existing installation is moved into `/userdata/system/theme-backups/`; the original Art Book Next theme and helper configuration are left alone.

```sh
(
  set -eu
  command -v curl >/dev/null
  command -v tar >/dev/null
  work="$(mktemp -d /userdata/art-book-next-1702.XXXXXX)"
  trap 'rm -rf "$work"' EXIT
  curl --fail --location --retry 3 \
    https://codeload.github.com/nschuster/art-book-next-1702/tar.gz/refs/heads/master \
    --output "$work/theme.tar.gz"
  tar -xzf "$work/theme.tar.gz" -C "$work"
  extracted="$work/art-book-next-1702-master"
  test -f "$extracted/theme.xml"
  test -f "$extracted/scripts/retroachievements/install.py"
  mkdir -p /userdata/themes /userdata/system/theme-backups
  target=/userdata/themes/art-book-next-1702
  if [ -e "$target" ] || [ -L "$target" ]; then
    backup="$(mktemp -d /userdata/system/theme-backups/art-book-next-1702.XXXXXX)"
    mv "$target" "$backup/theme"
    printf 'Previous theme saved in %s/theme\n' "$backup"
  fi
  mv "$extracted" "$target"
  printf 'Theme installed: %s\n' "$target"
)
```

**2. Install/update the achievement helper and sync.** New installations automatically use Batocera's saved login and Hardcore setting. Existing helper configuration is preserved. The installer adds the independent game-exit hook but does not enable startup syncing or change Batocera configuration. The optional startup service queues mapped achievement IDs using the progress-cache TTL; it is not needed for game-exit updates or the exit pipe-lifetime fix.

```sh
(
  set -eu
  python3 /userdata/themes/art-book-next-1702/scripts/retroachievements/install.py
  if [ ! -e /userdata/system/retroachievements/config.json ]; then
    python3 /userdata/system/retroachievements/configure.py
  fi
  python3 /userdata/system/retroachievements/sync.py \
    --config /userdata/system/retroachievements/config.json
)
```

Optional, only if you want startup refresh after a successful manual sync:

```sh
batocera-services enable ra_progress_sync
```

The valid service name uses underscores. Re-running the updated installer migrates the old `system/services/ra-progress-sync` only when its checksum matches the install manifest. Modified/unmanaged conflicts are refused without replacing them; restore the managed version or move your local file aside after review, then retry. The independent gameStop hook keeps its filename `ra-progress-sync.sh`. No Batocera service settings are automatically rewritten.

If sync reports missing/expired credentials, reauthenticate in Batocera's RetroAchievements settings and rerun block 2. If it reports **zero extras**, game IDs may need mapping; see the [helper guide](scripts/retroachievements/README.md). An existing manual Web API configuration stays unchanged; see that guide for migration rather than deleting it.

**Ambiguous ROM stems are skipped, not a library-wide failure.** Batocera uses one extras filename per system/ROM stem, so games sharing a stem (even across extensions, subdirectories or case, including unmapped games) cannot safely share progress. The helper skips the entire conflicting group, prints only group/game counts, and syncs the rest. You do **not** need to rename your whole library: leave affected games skipped, or give just those games distinct stems and update their gamelist/mapping paths. Previously generated, unchanged helper-owned extras for newly ambiguous groups are removed, even during targeted syncs. Unrelated/modified files are preserved; modified owned extras needing cleanup cause an explicit error rather than deletion.

**3. Restart EmulationStation from its menu**, after leaving any running game. Select **Theme Set → art-book-next-1702**, **Aspect Ratio → 4:3**, **Detailed** game-list view, enabled Game Metadata, and **Achievement Progress → On (sync helper required)**. Choose your preferred Color Scheme. These commands do not interrupt gameplay or change display settings.

### Alternative: Git or network copy

Via SSH (if Git is available on your Batocera installation):

```sh
cd /userdata/themes
git clone https://github.com/nschuster/art-book-next-1702.git art-book-next-1702
```

Alternatively, download this repository's ZIP on another computer, extract it, rename the extracted folder to `art-book-next-1702`, and copy it to `\\BATOCERA\share\themes\` over the network. The final layout must be `/userdata/themes/art-book-next-1702/theme.xml` (not an extra nested folder).

Restart EmulationStation, then select **User Interface Settings → Theme Set → art-book-next-1702**. In **Theme Configuration**, start with:

| Setting | Recommended value |
| --- | --- |
| Distribution | **Batocera/Knulli** |
| Aspect Ratio | **4:3** (force this for the Commodore 1702) |
| Game Metadata | **Release Date & Play Time** |
| Font Size | **Default** initially |
| Game Artwork | **Image** initially; all four existing choices remain supported |

Use the **Detailed** game-list view (not Basic); the exact game-list view selector location can vary by Batocera version. **On-Screen Help may remain enabled.** Automatic aspect selection also applies the fix when the framebuffer is recognized as 4:3. A physical 4:3 CRT can have a non-4:3 framebuffer; forcing this setting changes theme geometry, not video timings or pixel-aspect correction.

For updates to a Git installation, run `git -C /userdata/themes/art-book-next-1702 pull --ff-only`, then restart EmulationStation. For ZIP installations, replace this fork's folder with a fresh download. To roll back visually, select your original Art Book Next theme. Existing customizations intentionally still use `/userdata/theme-customizations/art-book-next/` so they remain compatible with upstream.

## Optional Commodore 64 palette

After updating and restarting EmulationStation, select **User Interface Settings → Theme Configuration → Color Scheme → Commodore 64**. Choose **Default** to return to the original colors. All existing schemes and the default selection are unchanged.

This candidate uses the **physical C64 breadbin and Commodore 1702 exterior**, not the blue BASIC screen: warm beige/ivory `#d8cfb6` on the metadata surface, dark brown `#302b26` on the list, charcoal `#292929` on help/menu surfaces, brown metadata text and muted gray icons. Cream list text becomes warm gold on selection. A short, subdued five-color Commodore-inspired rainbow underline uses the native textlist selector image; it occupies only the first fifth of the existing row width, without moving or resizing the list or media. This is an inspired palette, not a colorimetric reproduction of aged plastic. It covers system, game-list, menu, help, indicator and splash variables at every aspect ratio without changing fonts, original icons/artwork, or the approved seven-field panel. Existing menu foreground styling is retained. Custom splash artwork can still obscure the splash background.

The option name **Commodore 64** is retained. This palette uses the hardware exterior colors, not the blue BASIC screen. Players appears directly above Genre in the seven-field metadata panel.

Static previews: [320×240 enlarged](previews/commodore-64/metadata-240-enlarged.png) and [640×480 enlarged](previews/commodore-64/metadata-480-enlarged.png). These are XML/palette-aware compositions with sample game values and a sample help row, **not native Batocera screenshots**. The real game screenshot is not recolored. Generate with `python tools/render_metadata_panel.py --scheme commodore-64` (Pillow and CairoSVG required). Native font rasterization, dynamic help prompts, system/menu/splash rendering and physical CRT readability remain unverified.

## Optional RetroAchievements progress (Batocera 42)

**Achievement Progress → On (sync helper required)** moves Players beside Last Played, puts Genre at y=.76, and adds the same native Batocera achievement trophy immediately left of a smooth Commodore-rainbow bar below metadata (combined x=.55–.95; bar y=.815 and 22px height unchanged at 640×480). The trophy uses the exact game-name U+F091 glyph from ES's embedded FontAwesome font, not an emoji. The bar spans x=.5890625–.95, optically inset to match the metadata icon/value visible gap. A smaller `unlocked/total` count is centered inside, using normal sidebar text color with no badge. All seven fields and media geometry remain; Off retains the original layout. Palette changes need no sync, though older generated extras need a one-time refresh after upgrading. Sidebar alpha and the bright rainbow still limit count contrast in some palettes; see the guide. The optional Python helper automatically reuses Batocera 42's stored RA login token and known game IDs, caches both progress modes locally, and refreshes after game exit; startup sync is separately enabled. No username/API-key entry is needed. It reads enabled/hardcore settings each sync, ignores passwords and never writes Batocera configuration. No custom frontend binary or gamelist rewriting is required.

Follow the [installation and limitations guide](docs/RETROACHIEVEMENTS.md). Installing the theme alone does **not** fetch progress. Preview counts are fictional test fixtures, not your account. Native Batocera rendering, your account and actual CRT output still need device validation.

Already signed into RA in Batocera? Install/configure/sync without entering credentials:

```sh
python3 /userdata/themes/art-book-next-1702/scripts/retroachievements/install.py
python3 /userdata/system/retroachievements/configure.py
python3 /userdata/system/retroachievements/sync.py --config /userdata/system/retroachievements/config.json
```

Missing or expired token: reauthenticate in Batocera's RetroAchievements menu.
Existing manual Web API configurations remain supported; see the guide to migrate.

## Verification and limitations

Run `python -m pytest tests -q` from a Git checkout (includes the new token-backend subprocess tests as well as existing unittest cases). Tests require the upstream baseline commit `9a50ef366e750aabfab29e6915a2867607212971` and approved pre-palette revision `d3109da` in local history (use a normal, non-shallow clone). See [QA notes](docs/QA.md) for the engine revision, test-first evidence and geometry.

**Not hardware tested:** no Raspberry Pi 5, Commodore 1702 or running Batocera frontend was used for this candidate. Tests check conditions, native component types, bounds, original media geometry and unchanged layouts, not native rendering. Composite sharpness, overscan, native font scaling, long values and cropped-image marquee layering require on-device review. Metadata font size is deliberately fixed independently of the global font preset. Missing scraped dates and play-time records retain engine fallback behavior; a theme cannot recover missing data. Upstream screenshots below are not candidate screenshots. Current static approximations are under `previews/original-style/`; older preview directories show superseded designs.

---

# Original Art Book Next documentation
A simple theme based on the style of a coffee table book for distributions that use this fork of [EmulationStation](https://github.com/batocera-linux/batocera-emulationstation).  Specifically [Batocera](https://batocera.org/) (v40 and above), [Knulli](https://www.knulli.org/), [RockNIX](https://rocknix.org/) and [RetroBat](https://www.retrobat.org/)

## Preview
| ![system view](https://github.com/anthonycaccese/art-book-next-es/assets/1454947/c0252388-2268-444c-ae3d-07f15b87a98c) | ![menu](https://github.com/anthonycaccese/art-book-next-es/assets/1454947/39653703-f6e8-4940-98fc-66ce1c5af271) |
| -- | -- |
| ![gamelist-view-1](https://github.com/anthonycaccese/art-book-next-es/assets/1454947/e8251f3c-f033-43ed-8b55-f3a93c28131a) | ![gamelist-view-2](https://github.com/anthonycaccese/art-book-next-es/assets/1454947/fadfba3e-54a4-48e2-a11c-39c52797dc56) |

## Theme Configuration

The following options can be changed directly from the main menu under `User Interface Settings > Theme Configuration`

| Setting | Description | Options |
| -- | -- | -- |
| Distribution | Used to define which folder to look in for Theme Customization files. | `Batocera/Knulli`, `RockNIX`, `RetroBat` |
| Aspect Ratio | Enables you to select the correct aspect ratio for your screen.  This will automatically set itself so you should not need to change it but if the theme layout looks odd or spacing looks incorrect you can use this setting to make sure the aspect ratio matches your screen. | `16:9`, `16:10`, `4:3`, `3:2`, `1:1` |
| System Artwork | Defines the set of artwork that is displayed on the system view | `Default`, `Noir`, `Custom`, `Custom (Fullscreen)` |
| System Logos | Defines the logo set used on all views | `Default`, `Custom` |
| Game Artwork | Defines the type of artwork used to represent a game. These are sourced from the the selections you make in the scraper menu. Image will display the image you selected to scrape for `Image Source`.  Image (Cropped) will display that same image zoomed in to fill the screen.  Boxart will display the image you selected to scrape for `Box Source` | `Image`, `Image (Cropped)`, `Boxart`, `Logo` |
| Game Metadata | Sets if metadata (e.g. description, release date, etc...) should be displayed for a game | `On`, `Off` |
| Fonts | Define the fonts used throughout the theme. | `Default`, `Custom` |
| Font Size | Set the size for text elements throughout the theme. | `Default`, `Small`, `Large`, `Extra Large` |
| Color Scheme | Sets the color scheme that is used for the theme.  There is a set of prebuilt color schemes that you can select and an option to supply your custom color scheme (selected by choosing `custom`). You can see details on customizations below under [Theme Customizations](#theme-customizations). | `Default`, `Light`, `Steam OS`, `SNES`, `Famicom`, `OLED`, `Commodore 64`, `Custom` |
| Splash Screen | Toggles an optional custom splash screen which will be displayed when EmulationStation is loading and/or scanning for ROMs. | `Default`, `Custom` |

### Additional UI Settings 

The following EmulationStation settings can also be changed and will update the look of the theme accordingly:
* `User Interface Settings > Show Clock` - This will allow you to turn the system clock on or off
* `User Interface Settings > On-Screen Help` - This will turn the display of EmulationStation's help system on or off (the theme's layout will automatically adapt to the available space)
* `User Interface Settings > Show Battery Status` - This will allow you to change what is displayed for the battery status.

## Theme Customizations

Art Book Next allows customizations to system artwork and color schemes without the need to edit the source XML.  This enables you to change the look of the theme and still retain your changes when the theme is updated.

### Start Here
- Make sure the `Distribution` setting is set to the correct value for your current OS (e.g. Batocera/Knulli or RetroBat)
- This value determines the folder where you will add your customizations
    - Batocera/Knulli = `/userdata/theme-customizations/art-book-next/`
    - RockNIX = `/roms/_userdata/theme-customizations/art-book-next/`
    - Retrobat = `C:\RetroBat\emulationstation\.emulationstation\theme-customizations\art-book-next\`
- Create the folders that match your distribution and then move on to the options below...

### Background Art

The artwork used on the system view can be customized with your own images.

#### For angled artwork:

* Create your custom artwork using one of the masks i've supplied in this theme's resources directory [here](https://github.com/anthonycaccese/art-book-next-es/tree/main/resources/customizations). I've included a set of masks that should work in all major image editing programs.
* Export your final images as transparent pngs
* Create a folder in the path you created above called `artwork`
* Upload your images to that folder
* They can be named:
    * `_default.png`
    * `${system.theme}.png`
    * The theme will look them them up in that order. If a given image is not found in your folder then the the images from the theme will be used as a fallback.  This allows you to customize only the images you want and still have images displayed for all systems.
    * `_default.png` can be used for creating a single image that is used for all systems OR a fallback for systems that you did not create a custom image for (if you don't want to use the fallback that already exists in the theme)
    * `${system.theme}.png` should be named for the system you are looking to override. For example if you wanted to override the artwork for `snes` you would create an image called `snes.png` in the artwork folder.
* Once your images are in place you turn on custom images by changing the `System Artwork` setting to `Custom`

#### For fullscreen artwork:

* Create a folder in the path you created above called `artwork-fullscreen`
* Upload your images to that folder
* They can be named:
    * `_default.png`
    * `_default.jpg`
    * `${system.theme}.png`
    * `${system.theme}.jpg`
    * The theme will look them them up in that order.
    * `_default.png/jpg` can be used for creating a single image that is used for all systems OR a fallback for systems that you did not create a custom image for (if you don't want to use the fallback that already exists in the theme)
    * `${system.theme}.png/jpg` should be named for the system you are looking to override. For example if you wanted to override the artwork for `snes` you would create an image called `snes.png` or `snes.jpg` in the artwork folder.
* Once your images are in place you turn on custom images by changing the `System Artwork` setting to `Custom (Fullscreen)`

> If you create a set of images that you would like to share with the community please let me know about it [here](https://retropie.org.uk/forum/topic/33010/theme-art-book-next)

### Splash Screen

* Upload your image to the folder you created above
* It can be named:
    * `splash.png`
    * `splash.jpg`
* One your image is in place you turn on your splash screen by changing `Splash Screen` to `Custom`

### Color Schemes

You can create your own custom color scheme to use for the theme

* Download this template: https://github.com/anthonycaccese/art-book-next-es/blob/main/resources/customizations/colors.xml
* Upload it in the path you created above and make sure its called `colors.xml`
* Change any values in the template to the colors you prefer.
* I tried to make the values as self explanatory as possible but if you have questions regarding which property does what please don't hesitate to ask.
* After your colors are defined; in theme configuration change `Color Scheme` to `Custom`

### Logos

System logos can be customized by adding your own images

* Create a folder in the path you created above called `logos`
* Upload your images to that folder
* They can be named:
    * `${system.theme}.svg`
    * `${system.theme}.png`
    * The theme will look them them up in that order. If a given image is not found in your folder then the the images from the theme will be used as a fallback.  This allows you to customize only the images you want and still have images displayed for all systems.
    * `${system.theme}.svg/png` should be named for the system you are looking to override. For example if you wanted to override the logo for `snes` you would create an image called `snes.svg` or `snes.png` in the logos folder.
* Once your images are in place you turn on custom images by changing the `System Logos` setting to `Custom`

### Fonts

You can supply your own fonts for each of the font types defined in the theme

* There are 4 font types:
    * Bold: Used for the Clock, Battery, Gamelist, Game Count, Game Release Date, Game Play Time, Game Playcount, Menu Items
    * Regular: Used for Game Description, Menu Groups
    * Light: Used for Menu Footer
    * Logo: Used for System Names if a logo image does not exist
* Download this template: https://github.com/anthonycaccese/art-book-next-es/blob/main/resources/customizations/fonts.xml
* Upload it in the path you created above and make sure its called `fonts.xml`
* Create a sub folder in that same path called `/fonts` and upload your custom font for each type into it
* Add the filename for each font into the `fonts.xml` file 
* Once your fonts are in place you turn on custom fonts by changing the `Fonts` setting to `Custom`

## **Additional Notes**

### Media Scraping:

* To make game artwork look as good as possible the recommneded settings for the built-in scraper are:
    * Image Source = `Screenshot`
    * Box Source = `Box 2D`
    * Logo Source = `Wheel`

### Versions for other ES forks:
* If you use ES-DE... then the ES-DE version [here](https://github.com/anthonycaccese/art-book-next-es-de) will work out of the box with that distribution.  When used with ES-DE the theme comes with additional support for navigation sound sets.

### **Acknowledgments**
* Most system logos were sourced and modified from the excellent work done by Dan Patrick [here](https://archive.org/details/console-logos-professionally-redrawn-plus-official-versions).  I modified each to be compatible with EmulationStation's current SVG support.
* ChangaOne font is by [Eduardo Tunni](https://www.fontsquirrel.com/fonts/changa)
* Auto-Collection Genre background art created by [@nautipuss](https://github.com/nautipuss)
* Metadata Icons sourced from [FontAwesome](https://fontawesome.com/search?o=r&m=free)
* The `Noir` System Artwork set was created and provided by [tenlevels](https://www.reddit.com/user/tenlevels/) with help from f8less and inspired by the artwork from the Epic Noir theme by chicuelo
* Thank you to [GenoCL](https://genocl.carrd.co/) for the idea of the multi-artwork system view.  It got me to think about ES themes in a different way when building it out and it came out awesome.

## **License**
Creative Commons CC-BY-NC-SA - https://creativecommons.org/licenses/by-nc-sa/2.0/
You are free to share and adapt this theme as long as you provide attribution back to me (and the above credits) as well share any updates you make under the same license terms.

Thank you for taking a look at this 😄

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

## Install on Batocera

Keep the original theme installed for easy comparison/rollback. Install this fork into its **own** folder; do not overwrite `art-book-next`.

### Copy-paste directly on Batocera (no Git required)

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

**2. Install/update the achievement helper and sync.** New installations automatically use Batocera's saved login and Hardcore setting. Existing helper configuration is preserved. Startup syncing is enabled only after a successful sync; the installer also adds the game-exit hook.

```sh
(
  set -eu
  python3 /userdata/themes/art-book-next-1702/scripts/retroachievements/install.py
  if [ ! -e /userdata/system/retroachievements/config.json ]; then
    python3 /userdata/system/retroachievements/configure.py
  fi
  python3 /userdata/system/retroachievements/sync.py \
    --config /userdata/system/retroachievements/config.json
  batocera-services enable ra-progress-sync
)
```

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

# 4:3 metadata fix — verification notes

## Cause and deliberately narrow change

Upstream baseline: `9a50ef366e750aabfab29e6915a2867607212971` (anthonycaccese/art-book-next-es).

The shared theme hides native metadata initially. In `aspect-ratio-4-3.xml`, the release-date/rating view and the play-statistics stackpanel view both require `ifHelpPrompts="false"`. Consequently, enabling On-Screen Help suppresses every 4:3 metadata pair, while leaving the description visible. This fork removes those two guards and reserves space above the description when help is enabled. It does not introduce new metadata bindings or alter the original styles.

The existing Aspect Ratio subset already supplies both forced `4:3` (`4-3`) and Automatic (`4-3-auto`) activation. Select the separately installed upstream theme for the exact original help-on behavior; no new subset or global theme changes are necessary.

## Engine implementation inspected

Batocera EmulationStation revision: `b2ceb55a7e3d205a11f055b7d93c8be50cd6f9c9`.

- [ThemeData.cpp](https://github.com/batocera-linux/batocera-emulationstation/blob/b2ceb55a7e3d205a11f055b7d93c8be50cd6f9c9/es-core/src/ThemeData.cpp): format-7 nodes process in document order; conditional includes therefore override preceding shared views. `ifHelpPrompts` reads `ShowHelpPrompts`. Comma-separated subset clauses are conjunctive, pipe-separated values are alternatives. The production patch uses only existing schema properties.
- [DetailedContainer.cpp](https://github.com/batocera-linux/batocera-emulationstation/blob/b2ceb55a7e3d205a11f055b7d93c8be50cd6f9c9/es-app/src/views/gamelist/DetailedContainer.cpp): native release date is looked up as `datetime` / `md_releasedate`, and rating as `rating` / `md_rating`; these types remain intact.
- [DetailedGameListView.cpp](https://github.com/batocera-linux/batocera-emulationstation/blob/b2ceb55a7e3d205a11f055b7d93c8be50cd6f9c9/es-app/src/views/gamelist/DetailedGameListView.cpp): selection updates the detail container and theme-extra bindings.
- [StackPanelComponent.cpp](https://github.com/batocera-linux/batocera-emulationstation/blob/b2ceb55a7e3d205a11f055b7d93c8be50cd6f9c9/es-core/src/components/StackPanelComponent.cpp): horizontal layout sizes children within the panel and clips to its bounds. Long strings can be truncated, not automatically wrapped into another metadata row. The inherited fractional separator is scaled against parent **height** for horizontal orientation (the upstream `10` pixel comment is not exact at 640×480). No new separator or size assumptions were introduced.

This is an inspection of a pinned engine revision, not a claim that every Batocera release has been executed.

## Test-first evidence

Command: `python -m unittest discover -s tests -v`

1. Tests were added before any theme edits.
2. Initial harness run encountered upstream bare ampersands (`&&` and `fade & slide`) rejected by strict Python ElementTree. The resolver escapes bare ampersands in memory only; no upstream XML was normalized or rewritten.
3. Corrected RED run: **6 test methods, 97 failed assertions/subtests**. Release date stayed hidden, the horizontal panel was absent with help on, and the description occupied the metadata area. Existing unaffected-mode tests passed.
4. GREEN after the scoped XML change: **6 test methods pass**. Metadata visibility covers 96 combinations: explicit/automatic 4:3 × four font sizes × four artwork modes × three enabled metadata settings.
5. Additional regression checks compare help-off configurations, Basic/system views and Metadata Off against upstream; all other aspect files and the shared theme/font/color/splash files are byte-identical. Style and media properties of existing help-on components are also compared.

The small test resolver follows the include order, subset filters, help filters, name lists and property overrides used in these cases. It does **not** implement arbitrary engine expressions, native text shaping, font scaling, dynamic stackpanel layout, subset automatic detection, or game-data evaluation. Baseline comparisons require the upstream commit in Git history.

## Geometry (help enabled)

| Region | 640×480 | 320×240 |
| --- | --- | --- |
| Play-statistics / mixed row y bounds | 288–308 | 144–154 |
| Description y bounds | 312–402 | 156–201 |
| Description viewport height | 90 | 45 |
| Help background starts | 425 | 212.5 |

The metadata panel retains its 255-pixel width at 640×480. Description x/width, artwork, video and marquee geometry remain upstream. The smaller viewport still vertically scrolls the complete description; it does not concatenate metadata into or overwrite scraped description text.

## Outstanding device checks

- Not run in native EmulationStation; not tested on Pi 5 / Commodore 1702.
- Check actual composite-output readability and overscan at the user's output resolution.
- Try short/long descriptions, unknown release dates, never-played games, long play times and high play counts.
- Check all metadata selections with help on/off; Large/Extra Large may retain upstream clipping.
- Check artwork missing, video absent/present, and cropped-image marquee layering on device.
- Static screenshots in the original README are **upstream examples**, not screenshots of this patch. No synthetic preview is presented as native evidence; a separate preview was omitted to keep this minimal conditional/layout fix efficient.

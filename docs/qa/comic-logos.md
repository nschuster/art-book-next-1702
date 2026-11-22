# Comic system logo QA

## Contract

`system-logos:comic` / **Comic (Retrorama)** is added after Default and Custom. No persisted setting or default is changed. Four existing large-logo consumers are augmented: system extra, Custom Full Screen carousel logo, Basic/Detailed header, and Canvas `canvas-logo`. The selected PNG is white-tinted (`ffffff`, neutral multiplication) only when the actual comic file exists; otherwise the normal path and palette tint remain. System/Canvas text fallback is hidden if either logo exists. Tiny hardware carousel icons and game marquees remain untouched. Ratio includes and layout geometry are unchanged.

## Native semantics

Reference Batocera ES commit: `4adf26b43900d1a33887af6d8af3da2e99e398a5`.

- Parse-time `if` uses `Utils::MathExpr::evaluate` and evaluator variables, so the guard is `exists(${themePath} + "/_inc/systems/logos-comic/" + ${system.theme} + ".png")`, not an unevaluated variable inside a quoted string.
- Runtime BOOLEAN visibility includes `{system:theme}` to trigger expression binding. It checks both ordinary and comic paths.
- PATH loading preserves the prior property when a new path is absent, but explicit existence guards also keep the fallback tint correct.
- The independently compiled native MathExpr helper was exercised for all four normal/comic file-presence combinations: selection follows comic presence, and text is visible only when neither exists. This is expression validation, not a native frontend screenshot.

## Regression coverage

`tests/test_comic_logos.py` covers exact additive XML, option/default preservation, six aspect-ratio modes, seven artwork modes, system/Canvas/Basic/Detailed consumers, missing-image fallback, full colour, and unchanged non-target components. Default and Custom resolved properties are compared with published `f376e95f211fd345e87a129d8439a47345aff54e`. Native source contracts are checked when the pinned source is available.

Existing Canvas preservation tests allow only the explicitly added Comic path/tint/visibility properties; after removing those opt-in nodes, prior components must still match exactly. Original asset hashes remain unchanged.

The stable candidate's full suite uses the existing native playtime, launch-expression and SVG probes. Historical comparison tests require Git history in the export; a plain `git archive` is insufficient. Import local history with `git fetch --update-shallow` before running tests. The first no-history run is not a product regression result.

## Assets

56 pinned upstream logos, source Git blob/SHA-256 validation, documented transparent crop/proportional thumbnail only, 2px transparent margins, and derivative hashes. Independent review rebuilt every asset twice, matched pinned GitHub blobs and the three retained licence documents, and verified corrupt source rejection. See `../../_inc/systems/logos-comic/ATTRIBUTION.md` and its manifest. Import tooling assumes trusted repository manifest and output paths; it is not an untrusted-input sandbox or atomic installer.

## Limits

Static Pillow/CairoSVG Canvas previews demonstrate fitted real artwork and fallback, not live EmulationStation or CRT rendering. No physical device install, display timing change, loading-screen replacement, or forced setting change was performed. On device: select Comic, check a covered system and C64 fallback, toggle Canvas, check a game list and Custom Full Screen, and switch back to Default/Custom.

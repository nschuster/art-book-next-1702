# Native system playtime — local candidate

The user now accepts the original native days-containing format. This supersedes the no-days requirement in the historical `system-playtime-investigation.md`; that investigation is retained unchanged.

## Implementation

System Playtime → Off / On, Off first, independent of System Count. Only a new system text extra is included when enabled. Existing artwork, logos, count and every non-system view are unchanged. Shared count geometry is identical across ratios; playtime uses center `.5 .85`, height `.05`, width `.9`, original count font presets and white color. Count remains at `.5 .78` with height `.05`. Nominal footer clearance is .0104167 screen height (5px at 480p, 2.5px at 240p); native large-font ink and physical overscan need device review.

## Native source and executable check

Batocera 42 ES revision `4adf26b43900d1a33887af6d8af3da2e99e398a5`, checkout `/tmp/ra-es-source`. SystemData.cpp:2179–2217 returns formatted `gameTime` or Null at zero; aggregation sums visible games and therefore changes with filters. Formats are mm:ss, hh:mm:ss and dd:hh:mm:ss, with arbitrarily wider day counts within the native integer domain.

BindingManager.cpp:103–154 substitutes quoted strings but an empty replacement for Null. Its evaluated expression is distinct from display-default text. TextComponent.cpp:623–625 exposes **emptyTextDefaults**, not a property named bindingDefaults; false avoids Unknown placeholders. Theme uses `empty( {system:gameTime} ) ? "00:00" : {system:gameTime}`. Spaces inside the call are deliberate: the exact pinned parser rejects `empty()` but accepts `empty(  )` after Null substitution. Do not minify those spaces.

Executed the unchanged pinned MathExpr/HtmlColor parser using `/tmp/playtime-probe/system-probe`, with expressions extracted from the actual XML and BindingManager-style substitution. Null, empty string, minute/hour/day boundaries and 100-day string preserve native values or produce `00:00`. Results are saved in `previews/system-playtime-native/parser-results.json`. This is real parser execution with dependency stubs, not a native GUI or compiled BindingManager integration test.

## Regression and preview evidence

Tests were written first: missing component and registration failed; existing non-system preservation passed. Full include-graph tests cover independent count On/Off, help On/Off, all font presets and representative manual/automatic ratios. Ordered baseline transformation admits only the two new root nodes; original non-target XML is compared intact. The old palette and RA registration guards were extended only for those exact additions; unrelated uncommitted RA code/tests were not edited.

Static previews use original bundled SNES art and logo, Commodore 64 palette, sample count `128 GAMES` and sample native string `02:03:04:05`. They are **not screenshots or user library totals**. Renderer uses resolved geometry and palette, independently at 640×480 and 320×240. Help prompts and font/carousel rasterization are approximations; native animations, filters/refresh behavior, overscan and device readability remain unverified. No Recalbox assets or helper added. No commit or push.

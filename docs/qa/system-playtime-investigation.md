# System Playtime: blocked before runtime changes

Requested: independent **System Playtime → Off / On**, below System Count, with cumulative hours/minutes and never days. **Not implemented**: no option/include/layout was added, because the pinned parser does not provide the string extraction needed for a reliable general conversion. Existing theme, logos, art, palettes, game views and RA work remain untouched. No preview was generated for an unimplemented feature.

## Verified source and execution

Batocera 42 ES checkout `/tmp/ra-es-source` reports revision `4adf26b43900d1a33887af6d8af3da2e99e398a5`. `cmp` verified `/tmp/playtime-probe/MathExpr.cpp` and `.h` are identical to this checkout. Recompiled with:

```
g++ -std=c++11 -I/tmp/playtime-probe /tmp/playtime-probe/main.cpp /tmp/playtime-probe/MathExpr.cpp /tmp/playtime-probe/HtmlColor.cpp -o /tmp/playtime-probe/system-probe
```

This is the real unchanged parser and HtmlColor implementation with existing fail-fast dependency stubs; not a running EmulationStation build. Tested methods below execute within the parser (unsupported methods fail in its lookup); do not interpret filesystem/date stubs as native feature tests. No native GUI/device test was performed.

`SystemData.cpp:2179–2197` exposes case-sensitive `gameTime` as a **string**, formatted `mm:ss`, `hh:mm:ss`, or `dd:hh:mm:ss` (days have a minimum, not maximum, of two digits). Zero falls through to Null at line 2217. It is not raw seconds. `BindingManager.cpp:130–134` quotes strings in evaluable expressions; Null leaves an empty replacement. A numeric calculation consumes only the leading numeric prefix of a quoted string, losing the remaining components.

Real parser outputs:

| Expression | Output |
| --- | --- |
| `split("100:01:02:03", ":")` | `ERROR: Unknown method namesplit()` |
| `substr("100:01:02:03", 0, 3)` | `ERROR: Unknown method namesubstr()` |
| `substring("100:01:02:03", 0, 3)` | `ERROR: Unknown method namesubstring()` |
| `length("100:01:02:03")` | `ERROR: Unknown method namelength()` |
| `replace("100:01:02:03", ":", "")` | `ERROR: Unknown method namereplace()` |
| `tointeger("100:01:02:03")` | `ERROR: Unknown operator: 100 : 1.` |
| `("100:01:02:03" * 24)` | `2400` (loses 1h 2m) |
| `contains("100:01:02:03", ":")` | `1` |

The complete method registry is `MathExpr.cpp:44–96`; string methods include empty/case/trim/proper, conversion, contains/startswith/endswith, but no substring, indexing, splitting, replacement or length. Arithmetic and shift operators do not slice strings (`827–848`). A giant enumerated pattern-matching lookup is not a verified general-purpose formatter and was not shipped. This is an engineering blocker for a reliable maintainable theme-only expression, not a claim that no finite lookup could ever be encoded.

## Boundary negative controls

Ran `python /tmp/playtime-probe/system-boundaries.py` with actual parser evaluation of the existing raw-seconds-style hours expression after replacing the binding as BindingManager does. All negative-control assertions passed (they assert this unsuitable expression fails, not that the requested feature works).

| Seconds | Native binding | Required | Actual unsuitable arithmetic |
| ---: | --- | --- | --- |
| 0 | Null | 0h 0m | unary `/` error |
| 1 | 00:01 | 0h 0m | 0h 0m |
| 59 | 00:59 | 0h 0m | 0h 0m |
| 60 | 01:00 | 0h 1m | 0h 0m |
| 3599 | 59:59 | 0h 59m | 0h 0m |
| 3600 | 01:00:00 | 1h 0m | 0h 0m |
| 86399 | 23:59:59 | 23h 59m | 0h 0m |
| 86400 | 01:00:00:00 | 24h 0m | 0h 0m |
| 172800 | 02:00:00:00 | 48h 0m | 0h 0m |
| 8640000 | 100:00:00:00 | 2400h 0m | 0h 1m |
| 8643723 | 100:01:02:03 | 2401h 2m | 0h 1m |
| 18000000 | 208:08:00:00 | 5000h 0m | 0h 3m |

## Binding/schema and layout discovery

Source supports dynamic system text: `SystemView.cpp:642–654` updates selected system background extras, called from `onCursorChanged` at line 714. `ThemeData.cpp:1683–1730` records binding expressions as property-name + `_binding`; `BindingManager.cpp:232–252` evaluates non-single-variable string expressions and updates the property. This is source verification, not compiled binding-manager or live refresh testing. Binding capability itself is not the blocker.

Existing `theme.xml:82–85` registers **System Count → Off / On**, Off first. Count extras live at lines 331–354: center `.5 .78`, height `.05`, with separate zero/singular/plural bindings. Aspect-ratio includes are loaded after the shared system view at lines 802–806, then the unrelated optional RA include. A future System Playtime include should stay independently gated and avoid moving these existing elements. No layout or 640×480/320×240 claims are made for a feature that was not implemented.

## Next decision

A native raw-total-seconds or cumulative-hours binding (or parser string-slicing support) would unblock clean theme-only rendering. A generated total would require a helper, outside the requested no-helper scope. Showing the native colon string would expose days, contrary to the explicit hours-highest requirement. Neither compromise was silently substituted.

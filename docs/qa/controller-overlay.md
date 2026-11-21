# Controller overlay: clock-size battery and palette feedback

## Implemented

Controller battery nominal font requests now match the existing `system-clock`
for every Font Size preset at 640×480 and 320×240. This uses the authorized stock
workaround: enlarge controller icon height proportionally, retaining the first
icon's position, left alignment, spacing, artwork, idle color and clock/layout.
The row can grow; its width is not a clipping boundary.

Both ordinary-input `activityColor` and `hotkeyColor` use `${menuSelectorColor}`;
idle remains `${systemIndicatorColor}`. Native percentage text shares that state
color. Existing accents are Default/Light/OLED `444444`, Steam OS `324d6c`, SNES
`514689`, Famicom `4d1116`, Commodore 64 `65513c`, Custom `444444` fallback with
user overrides. Custom contrast remains the palette author's responsibility.

## Native contract and sizing

Source pin: Batocera ES `4adf26b43900d1a33887af6d8af3da2e99e398a5`.

- `ControllerActivityComponent.cpp:201–255`: square icon dimensions are
  `mSize.y()`; battery font is `Font::get(height * (isSmallScreen ? .55 : .70),
  FONT_PATH_REGULAR)`. There is no independent supported battery font property.
- **Native dynamic selection is available:** `ThemeData.cpp:1250–1258` implements
  the `tinyScreen` filter using `Renderer::isSmallScreen()` directly; property
  parsing calls `parseFilterAttributes(node)` at 1929–1932. The six conditional
  `size` values therefore select .55 vs .70 correctly, including ForceSmallScreen
  overrides. No invented property or inferred aspect-ratio heuristic is used.
- `Renderer.cpp:976–983`: the default small-screen condition is width ≤480 OR
  height ≤480; ForceSmallScreen overrides it. Widescreen uses whichever native
  condition applies, not necessarily .70. Landscape sizing matches the clock;
  portrait is not a parity target because clock sizing uses the minimum screen
  dimension whereas component height uses screen height.
- `theme.xml:276–283`: the actual clock has literal per-preset fontSize values
  (there is no shared clock-size variable): small/default 16/480, large 20/480,
  xlarge 24/480. These—not the indicator panel height or menu font—determine the
  new icon height. Tests extract the actual resolved clock fontSize so drift fails.
- `Font.cpp:1137–1151`: themed font request truncates float32 minimum screen
  dimension × fontSize to integer. The battery request also truncates to integer.
  Height literals include a tiny epsilon to avoid float32 underflow below the
  intended integer. Both use normal FontScale, not menu scaling (`Font.h:47`,
  `Font.cpp:156–173`), so equal requests receive equal scale.

| Preset | Nominal font 640 / 320 | Small-screen icon height 640 / 320 |
| --- | --- | --- |
| Small / Default | 16 / 8 | 29.09 / 14.55 px |
| Large | 20 / 10 | 36.36 / 18.18 px |
| Extra Large | 24 / 12 | 43.64 / 21.82 px |

Normal default font scaling is 1.31 at 640×480 and 1.5 at 320×240. These are
nominal request comparisons, not equal glyph bounds: the clock remains themed
bold and native controller text remains regular. Menu Font Size is unrelated.
The first icon remains at (20,20) or (10,10), respectively. No clock change.

## Multi-controller width and limits

Native rendering advances by icon width + spacing + measured `"100% "` width +
spacing per battery-bearing pad (`ControllerActivityComponent.cpp:304–335`).
Left alignment ignores the component width for row placement and there is no
component clip. Increasing size.x would not solve overflow; no wrapping or pad
limit is themeable here. Unknown battery levels omit the percentage.

Tests calculate that stride using a conservative **four scaled em text budget**
(not a native glyph measurement), preserving the rightmost quarter for indicators:
460px available at 640×480, 230px at 320×240 from the fixed first anchor. Two
battery-bearing controllers fit that budget at every preset and both native
small-screen states; eight icon-only pads also fit. Eight percentages exceed the
budget and may collide with indicators or leave the screen. Extra host indicators,
custom FontScale, more controllers and device-specific fonts need on-device checks;
the reserved quarter is a planning boundary, not a native clipping guarantee.
Disable SHOW CONTROLLER BATTERY LEVEL if a large multi-pad row becomes crowded.

## Verification boundary

Tests cover all presets/resolutions, both tinyScreen branches, float32/integer
font requests, source schema/filter/render contracts, palette tokens, toggle and
all unrelated screen/view preservation. The Python ordered include resolver is
extended locally for tinyScreen; it is not execution of the native XML parser.
No native controller rendering harness is available, no device rendering is
claimed, and no synthetic screenshot is presented as native evidence. Verify
real battery data and input flashes, reload the theme after changing presets,
and check multiple controllers on hardware. Independent font-face parity still
requires frontend support; the authorized height workaround is implemented.

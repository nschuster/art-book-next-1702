# System playtime: total hours and minutes (candidate)

## Result and scope

The system row now accepts a separately generated **saved-library total**, e.g. `51h 4m`, with hours as the highest unit. Zero is `0h 0m`; 100 days + 1h 2m is `2401h 2m`. No frontend rebuild and no RetroAchievements dependency. Existing System Playtime Off default, System Count independence, fonts, origin/position/size and non-system views are unchanged. Missing generated totals show `Playtime unavailable`, never a misleading zero or rejected colon timecode.

This is **not** a live native visible-games total: it sums every `<game>` in explicitly mapped saved gamelist XML (including hidden/filtered or stale entries), ignores `<folder>` records, and cannot see unsaved ES memory. Collections/group systems need their own explicit mapping; they are not guessed. Refresh after gamelist persistence, then reload the theme. No polling, automatic startup/gameStop hooks, restart, Ports installation or RA integration is installed by this script. Parent-owned Ports integration must honor these semantics.

## Local helper interface

Python standard library only. One independently runnable example from the actual theme directory (adjust only if the installed theme folder differs):

`python3 scripts/system-playtime/refresh.py --system snes=/userdata/roms/snes/gamelist.xml --system nes=/userdata/roms/nes/gamelist.xml`

`--system` is repeatable and takes native **system.name**, not fullName or theme alias. Default output is `/userdata/system/configs/art-book-next-system-playtime`; `--output DIRECTORY` supports isolated testing. `system-playtime.xml` includes `${system.name}.xml` there after defining the existing text component. Generated includes override **only its text**. Missing includes follow the frontend's existing optional-file behavior. Theme activation remains System Playtime → On. No gamelist is modified.

Outputs are atomic per file; a SHA-256 ownership journal refuses unmanaged/modified destinations and symlinks. All input parsing and output-conflict checks happen before writes. Invalid/negative/fractional gametime aborts with a secret-free error; prior totals remain and may be stale. This minimal explicit CLI is not a concurrent daemon or a multi-file transaction: interrupted I/O can require manual recovery of owned output/journal. Omitted systems are retained (targeted refresh), not automatically deleted. To disable, choose Off; no helper process remains running. Do not silently enable periodic or concurrent runs.

## Native limitation actually checked

Batocera 42 ES source pin: `4adf26b43900d1a33887af6d8af3da2e99e398a5`.

- `SystemData.cpp` property registry at the top exposes no raw aggregate seconds. `getProperty` 2179–2197 returns `mm:ss`, `hh:mm:ss`, `dd:hh:mm:ss`; zero returns Null. Days have a minimum width, not a two-digit maximum.
- `MathExpr.cpp` 44–96 registers no substring/split/replace/length operations. `tointeger` only removes quotes, so colon text is not parsed as seconds. String predicates do not offer a general field extraction operation.
- Rebuilt unchanged MathExpr.cpp and HtmlColor.cpp after byte-comparison to the pinned checkout, using existing dependency-only stub headers. The first build failed because that temporary filesystem stub lacked `sys/stat.h`; `-include sys/stat.h` fixed compilation. Actual parser outputs: `substr`, `split`, `replace` → Unknown method; `tointeger("02:03:04:05")` → Unknown operator `2 : 3`. Null fallback works but does not convert nonzero durations.
- These facts establish no practical generic native hours conversion for the shipped system binding; the per-game raw-seconds expression must not be applied to it.

## Verification

Strict RED before production edits: `python -m pytest tests/test_system_hours_helper.py -q` produced **16 failed, 4 passed** (helper absent and runtime still raw timecode). Log `/tmp/system-hours-red.txt`. The negative safety tests only became meaningful after the helper existed; the final suite exercises real subprocesses and real files.

GREEN: `SYSTEM_HOURS_NATIVE_PROBE=/tmp/system-hours-native-probe python -m pytest tests/test_system_hours_helper.py tests/test_system_hours_native.py tests/test_system_playtime.py -q` → **38 passed**.

Native rebuild used:

`g++ -std=c++11 -include sys/stat.h -I/tmp/launch-expression-probe /tmp/launch-expression-probe/MathExpr.cpp /tmp/launch-expression-probe/HtmlColor.cpp /tmp/launch-expression-probe/main.cpp -o /tmp/system-hours-native-probe`

Those temporary dependencies came from the inspected existing probe and are not repository prerequisites. Native tests skip unless an explicitly rebuilt pinned probe is supplied. MathExpr SHA-256: `409344b9d1dbd8b6d1d79801d7473cc96b0bd86f242704f5361a9a41ce6c9870`; HtmlColor SHA-256: `a7a0711f889f7799773f46a20fe331f799905df260b3cb42e6f28617516fc795`. The native tests clearly label all binding inputs as source-format fixtures, not real user/library bindings. They cover Null, empty and every binding width through 100-day strings. The helper tests cover matching second boundaries and large totals with exact Python integer arithmetic.

Native parser execution is not a full BindingManager build, native GUI rendering, on-device refresh proof or CRT readability approval. No device access, commit or push performed.

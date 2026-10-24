# RetroAchievements per-game extras helper (Batocera v42)

This is an optional, short-lived **Python 3 standard-library** synchronizer, not an
emulator plugin or daemon. It never modifies a gamelist and never reads Batocera
credentials. Supply your RA **web API key**, not your password/token. No live RA
requests or device tests were performed during development: tests use an explicitly
injected loopback HTTP server and synthetic fixture counts.

## Theme integration contract

Default output:

```
/userdata/system/retroachievements/extras/<system>/<ROM stem>.xml
```

Each document is `<theme><formatVersion>7</formatVersion><view name="detailed,video">`
with `<text name="ra_progress" extra="true">`, position `0.75 0.837916666666667`,
size `0.14 0.045833333333333`, font `${themePath}/${fontBold}`, fontSize
`0.027777777777777` (16.67% smaller count only), origin `0.5 0.5`, multiLine false,
center alignment, zIndex 101, visible true, color
`${gamelistListTextlistUnselectedColor}` (normal sidebar text) and text `earned/total`. The theme must point its
`<gameextras name="gameextras"><path>…</path></gameextras>` at the **selected
system's directory**, not the shared extras root. Coordinate this with the theme's
4:3 opt-in. There is no badge background or separate count row. Text properties plus `label` are
configurable in `template`; width/font suitability still needs native CRT QA.

The second extra is `<image name="ra_progress_bar" extra="true">`, position
`0.55 0.815`, size `0.40 0.045833333333333`, origin `0 0`, white tint, and an absolute SVG
path. This transparent image contains only the exact unlocked/total vector fill;
the smooth Commodore rainbow spans that filled portion (not the whole track).
0/0 and zero unlocked produce an empty track. This uses native image properties
verified in pinned ES `ThemeData.cpp`, not a preview-only drawing. A separate white
`ra_progress_track` SVG at the same geometry (zIndex 99) is tinted with
`${gamelistListTextlistBackgroundColor}`. Palette switches require no re-sync.
Both SVGs use preserveAspectRatio="none". Sidebar alpha is retained: Famicom is
still faint on the empty track, while C64 ivory is now clear. Both lose contrast
over the full rainbow. No badge/shadow was added. See the final-text gallery and main guide.

Assets live in `system/retroachievements/assets/<sha256>.svg`. A separate
checksum ownership journal is written before creating an asset. Collection at the
end of each sync retains referenced assets from the full XML manifest, including
offline/untargeted games, and deletes only unchanged owned unreferenced SVGs.
Thus ordinary repeated refreshes retain one common track plus one fill per displayed
ratio, not every historical count. Unrelated/modified assets are left alone;
modified owned XML defers collection conservatively. Do not manually edit the
managed files or reference these private assets from unrelated XML. Interrupted
writes are reconciled on the next completed sync. Uninstall retains these assets.

Batocera loads ROM **stem**, not relative ROM pathname. Therefore two same-stem
ROMs anywhere within one system are unsafe: the sync aborts before requests/writes
when collisions occur in its configured gamelists/mapping, including unmapped
entries. It does not inventory ROM files absent from gamelists; ensure filenames
are unique. Cross-system identical stems are safe. A checksum-backed ownership
manifest reconciles generated extras against the full mapping, even during targeted
refreshes: removed/remapped games and account/mode changes invalidate old output
before fetching. Unrelated or locally modified XML is not silently deleted or
overwritten. Do not repurpose this helper's output directory for unrelated extras.

## Install and configure

Assuming this repository is installed at `/userdata/themes/art-book-next-1702`:

```sh
python3 /userdata/themes/art-book-next-1702/scripts/retroachievements/install.py --data-root /userdata
```

The installer creates only its own helper, examples, mapping and two uniquely named
hooks. It **does not enable** the startup service or modify `custom.sh`, existing
services, theme files or gamelists. Repeating installation is idempotent; unmanaged
or locally modified generated files are refused instead of overwritten. A manifest
tracks generated file hashes. Managed upgrades roll back on write failures.

Create a first-run private config without hand-editing JSON:

```sh
python3 /userdata/themes/art-book-next-1702/scripts/retroachievements/configure.py --data-root /userdata --mode hardcore
```

This prompts for username and a hidden web API key, discovers systems with existing
gamelists, writes mode 0600, and refuses to overwrite an existing config. It does not
contact RA. Review the discovered systems before syncing. The empty template uses current defaults.

Alternatively create `/userdata/system/retroachievements/config.json` by copying the supplied
`config.example.json` **only if no config already exists**. Set `username` and
`api_key`, list your systems, choose `hardcore` or `softcore`. Keep `template: {}`
for current native bindings. Remove obsolete overrides when upgrading, reinstall
the helper and sync once; later palette changes need no refresh. An explicit
fontPath override must be absolute. Then:

```sh
chmod 600 /userdata/system/retroachievements/config.json
python3 /userdata/system/retroachievements/sync.py --config /userdata/system/retroachievements/config.json --data-root /userdata
```

The config must be owned by the invoking user and inaccessible to group/others.
The supplied example contains placeholders, not credentials. Do not commit your
private config. Errors never print response bodies, exception URLs, or API keys.

Optional startup enablement, after the manual sync works:

```sh
batocera-services enable ra-progress-sync
batocera-services start ra-progress-sync
```

The installed `/userdata/system/scripts/ra-progress-sync.sh` responds only to
`gameStop`, refreshes the exited system/ROM with `--force`, and exits after spawning
a short-lived worker. Startup refreshes the configured set using the cache TTL.
Both use the same nonblocking advisory `flock` inside Python: overlapping work is
skipped, not queued. Thus a game exit during a long startup scan can be skipped;
a later manual forced sync can recover it. Hooks redirect output to `/dev/null`;
run the manual command for a summary. No periodic daemon or unbounded log exists.

Rollback (cache/config remain for reinstall):

```sh
batocera-services disable ra-progress-sync
python3 /userdata/themes/art-book-next-1702/scripts/retroachievements/install.py --data-root /userdata --uninstall
```

Uninstall removes only manifest-owned, unchanged helper/hook files. It does not
remove private config, JSON cache, XML extras, or unrelated services. Disable the
theme's RA option separately if desired. A currently running one-shot can finish;
the service is not a supervised daemon and `stop` deliberately does not kill it.

## Game identity: no generic ROM MD5

The helper first reads positive `cheevosId` values from
`<data-root>/roms/<system>/gamelist.xml` for configured `systems`. These are real
metadata fields in the pinned v42 source, **not scraper `id` attributes**. Batocera's
native achievement identification path uses console-aware rcheevos hashing (with
console-specific archive/header/disc handling). Enable/run the native achievements
identification process in Batocera and save gamelists first. IDs may be absent until
that process runs; this helper does not claim every stock gamelist already has one.

Reliable fallback/override: edit `mapping.json`, a JSON list with explicit
system + relative ROM path + verified RA game ID:

```json
[
  {"system": "snes", "rom": "./Super Mario World.sfc", "game_id": 228}
]
```

This example is a **mapping shape**, not a claim that a particular dump/revision is
compatible: verify the game's RA page/hash list. Paths can be absolute beneath that
system's `<data-root>/roms/<system>` or relative to it. `..`, control characters,
backslashes, unsafe systems, and output symlinks are refused. Explicit records
override matching gamelist IDs. Missing IDs are skipped; there is no guessed match
by filename/title and **no hashing of ROM bytes** in Python. The SHA256 use in this
helper is solely cache-account namespacing and installer file ownership, not RA
identification. A `cheevosHash` without `cheevosId` is not resolved by this helper;
use Batocera's native lookup or the explicit mapping fallback.

## API / cache behavior

Production endpoint is fixed HTTPS:
`https://retroachievements.org/API/API_GetGameInfoAndUserProgress.php`
with `y=<web API key>`, `u=<username>`, `g=<game ID>`. Redirects are refused to avoid
credential forwarding. `hardcore` selects `NumAwardedToUserHardcore`; `softcore`
selects `NumAwardedToUser` (includes achievements also earned hardcore, not a
softcore-minus-hardcore calculation). Denominator is `NumAchievements`.

Cache namespace is username-specific and stores only validated ID/count fields;
keys and full API responses are never persisted. XML/JSON writes use temporary
files, fsync and atomic replacement. Valid existing XML remains unchanged when
refresh fails, including forced/expired refreshes. Summary exit codes: 0 success or
lock-held skip; 1 one or more games failed (old files retained); 2 rejected setup.
Cached successful counts deduplicate same-ID requests across ROM aliases.

TTL defaults to 900 seconds; `--force` bypasses it. At least one second between
production request starts, bounded exponential retry backoff, at most four retries,
15-second HTTP timeout and 8 MiB response limit. 429/5xx/network failures retry;
other HTTP statuses and malformed responses do not. Retry-After is not interpreted;
backoff is capped at 30 seconds. Overall duration scales with library size; use
`--system snes --rom './Game.sfc' --force` for a targeted refresh. A failure never
creates a fake `0/0`. Offline retention applies only to the same account, mode,
ROM and game ID. Identity changes invalidate owned XML, so a failed refresh does
not display another account's or game's counts. Avoid editing mapping/config
concurrently with an active sync.

## Verified sources

Inspected Batocera ES commit `4adf26b43900d1a33887af6d8af3da2e99e398a5`:

- [MetaData.cpp](https://github.com/batocera-linux/batocera-emulationstation/blob/4adf26b43900d1a33887af6d8af3da2e99e398a5/es-app/src/MetaData.cpp): `cheevosHash`/`cheevosId`, lines 94–95.
- [FileData.cpp](https://github.com/batocera-linux/batocera-emulationstation/blob/4adf26b43900d1a33887af6d8af3da2e99e398a5/es-app/src/FileData.cpp): `checkCheevosHash`, lines 1605–1623.
- [RetroAchievements.cpp](https://github.com/batocera-linux/batocera-emulationstation/blob/4adf26b43900d1a33887af6d8af3da2e99e398a5/es-app/src/RetroAchievements.cpp): console-specific hashing, lines 574–646; [cheevos.cpp](https://github.com/batocera-linux/batocera-emulationstation/blob/4adf26b43900d1a33887af6d8af3da2e99e398a5/external/libcheevos/cheevos.cpp) invokes `rc_hash_generate_from_file`.
- [DetailedContainer.cpp](https://github.com/batocera-linux/batocera-emulationstation/blob/4adf26b43900d1a33887af6d8af3da2e99e398a5/es-app/src/views/gamelist/DetailedContainer.cpp): `gameextras` element lookup lines 424–441; stem/CRC fallback and `appendFile(path,true)` lines 735–782.
- [ThemeData.cpp](https://github.com/batocera-linux/batocera-emulationstation/blob/4adf26b43900d1a33887af6d8af3da2e99e398a5/es-core/src/ThemeData.cpp): `<theme>` root and parseTheme in appendFile, lines 2671–2708; extra=true converted to per-game extra.
- [Official RA endpoint documentation](https://api-docs.retroachievements.org/v1/get-game-info-and-user-progress.html): query parameters and softcore/hardcore count field names.
- [Batocera script documentation](https://wiki.batocera.org/launch_a_script): gameStop arguments `(event, system, emulator, core, ROM)` and separately named user services. This wiki is current, not pinned to v42; actual startup/event execution still needs device verification.

## Local verification / TDD evidence

```sh
python3 -m unittest discover -s tests -p test_ra_sync.py -v
```

Observed RED before implementation: 5 positive behavior tests failed because the
sync script was missing. GREEN: 8 tests passed. Next RED: installer and targeted
CLI filtering failed (missing installer / unrecognized arguments). GREEN: 11 tests
passed. Added regressions then observed RED for an unmapped same-stem collision
and duplicate retry of a shared failed ID; fixed both. Additional coverage includes
permissions, traversal, symlinks, XML escaping, separate hardcore/softcore counts,
real subprocess + local HTTP transport, endpoint query parameters, cached request
deduplication, offline preservation, redaction, gamelist byte preservation,
explicit overrides, locking, external mock-host rejection, installer idempotence,
rollback and unrelated-file preservation. Tests never contact RA.

`--test-api-base http://127.0.0.1:<port>/API/` is an explicit test-only injection,
not a live-service substitute. Use a temporary `--data-root` for tests. Native ES
rendering, Batocera hook lifecycle, real login/API compatibility, account-specific
achievement matching, physical CRT clipping/readability and startup networking
remain on-device acceptance checks.

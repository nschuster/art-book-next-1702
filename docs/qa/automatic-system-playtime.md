# Automatic background system playtime

Candidate implementation; not yet published or installed on the user's device.

## Approved behavior

The user chose background snapshot updates after games, with displayed totals catching up on a later theme reload. No frontend restart, HTTP reloadgames request, startup scan, RA login or API access is added. Ports Y installs/updates the independent hook and performs a recovery-aware initial refresh. RA A/X behavior is separate.

## Native contract

Inspected Batocera 42 ES revision `4adf26b43900d1a33887af6d8af3da2e99e398a5`:

- `es-app/src/FileData.cpp:713–775`: both launcher gameStop and ES game-end precede metadata updates. Successful sessions update gametime only after at least ten elapsed seconds, then call `saveToGamelistRecovery`.
- `es-app/src/Gamelist.cpp:21–23,217–230,266–314`: recovery directory is the user ES configuration's `recovery/<system>`; recovery `parentHash` is base gamelist byte size. Recovery writes are not atomic. Main gamelists are normally saved later.
- `es-core/src/ThemeData.cpp:1040–1092` parses the generated include during theme loading. Returning to the carousel does not reread it.
- `es-app/src/services/HttpServerThread.cpp:520–530` offers full-library reload, not a lightweight system-text refresh. It is intentionally unused.

Batocera release-tag source `batocera-42/package/batocera/core/batocera-configgen/configgen/configgen/emulatorlauncher.py:162–167,335–345` dispatches synchronous gameStop scripts before returning to ES. Therefore the installed hook captures a subsecond timestamp before spawning, detaches all worker stdio and returns promptly. A synchronous wait would prevent the metadata save it is waiting for.

## Implementation boundaries

- Installed helper: `/userdata/system/art-book-next-playtime/`.
- Independent hook: `/userdata/system/scripts/art-book-playtime.sh`.
- Generated totals: `/userdata/system/configs/art-book-next-system-playtime/`.
- Default worker timeout: 120 seconds, bounded polling. No forever-running service.
- Only the played native system's gamelist/recovery is parsed on exit; configuration discovery is still performed. Manual Y refreshes all discovered saved systems.
- Recovery overlays replace matching normalized ROM paths using the configured ROM root, including fallback gamelists stored outside ROM directories. Newly saved games can contribute to an existing base. Duplicate/invalid/ambiguous paths fail closed, and mismatched recovery parent hashes are skipped.
- Existing base gamelist required. Recovery-only systems without a base are unsupported. No guessed session-duration arithmetic or gamelist/recovery writes.
- Freshness is based on saved-file timestamps plus stable read signatures; this requires a coherent filesystem clock. Legacy second-only CLI timestamps retain conservative handling; installed hooks use subsecond time to avoid missing quick saves before the worker's first read.
- Output lock covers snapshot calculation/publication. Lock contention is retried. Write-ahead old/new-hash records recover interrupted output commits without accepting genuine user modifications.
- Installer manages only its whitelisted files with separate checksum ownership and recoverable install transaction; totals and RA state are not uninstalled.
- CLI writes a bounded fixed-schema `.last-result.json` (last completed operation, not a live progress stream) without game names, paths or exception details. Unsafe status paths are preserved.
- If initial refresh fails after install, Ports explicitly distinguishes background installation success from total refresh failure.

## Validation

New tests exercise real source and installed CLI paths; the actual generated hook is invoked with native argument ordering. In a temporary fixture it returns before recovery data exists, then a native-shaped saved record changes the generated total from `12h 0m` to `12h 30m`. Base gamelist bytes remain unchanged and no achievements directory is created. Separate tests cover saved-record overlays, stale hashes, malformed input, same-second timing, concurrent locks, symlink/unmanaged output refusal, interrupted ownership commits and sanitized status.

Stable clean-candidate gate: **399 passed, 1 skipped, 104 subtests passed** with the available native source/probes enabled. Independent review ran **88 focused tests**, all passing, including generated-bootstrap byte-for-byte reproducibility. An additional independent fault probe passed eight real SIGKILL publication-boundary cases; installer tests separately exercised fresh/update/uninstall restart boundaries.

The packaged overlay was extracted and its actual standalone bootstrap run in an isolated userdata fixture: exit 0, independent hook installed, saved total `1h 30m`, no RA state created. The real SDL companion success screen was captured at 640×480 and visually checked: all status and control text fits. These are Linux fixture/SDL checks, not physical Batocera/CRT or live frontend validation.

No GitHub commit/push or device installation was performed.

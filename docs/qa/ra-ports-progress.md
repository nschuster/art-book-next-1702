# Optional Ports RetroAchievements progress screen

## Scope

An opt-in managed Ports shell entry starts a Python/SDL2 display. After display
initialization succeeds, it attaches to an existing worker or starts the existing
queue worker with `--force --watch` in a separate session. No new authentication
flow, ROM hash pass, frontend patch, game-list rewrite or automatic library sync
is installed. Ordinary game-exit hooks remain unchanged.

Worker-owned `progress.json` publishes console/game names, unique queued game-ID
counts, cache/update counts and retry/terminal states atomically under `sync.lock`.
Names come from existing gamelist mappings and system fullnames, with bounded,
normalized, credential-redacted fallbacks. Queue contenders cannot overwrite the
owner's status. Token achievement definitions retain their existing cache.

The UI's read-only session adapter additionally detects a worker exiting before
it can publish (bad configuration/discovery), and abrupt termination. It does not
write synthetic results to the worker status file. Startup discovery has no known
total; this is displayed as scanning rather than a fabricated percentage.

Managed install/uninstall preserves configuration, unowned files and other Ports.
Installer and launch locks protect the pre-lock worker startup interval as well as
normal processing. A process-start identity guards against recycled PIDs.

## Executed local checks

From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 BATOCERA_ES_SOURCE=/tmp/ra-es-source python -m pytest tests -q -p no:cacheprovider
git diff --check
```

Result: **189 passed, 104 subtests passed**, 73.57 seconds; whitespace check clean.

Final review regressions also pass: launch releases `sync.lock` before spawning;
UI polling never takes that lock; the first full-library request queues behind an
existing one-game hook without repeated launches resetting generations; removed
queued IDs do not inflate totals; HTTP and queue retry attempts have distinct labels.

The suite includes:

- Real CLI workers against explicitly loopback-only HTTP fixtures; no account calls.
- Worker lock contention, queue additions, deduplicated IDs, cache bypass, retained
  definitions, retry recovery/exhaustion, source restart, cancellation and failures.
- Optional install, retained opt-in on upgrades, uninstall ownership, unchanged
  configuration and pending queue, and refusal to replace an unmanaged Ports file.
- An **installed** launcher opening real SDL with a dummy video driver, initiating
  a fixture worker, showing its current game, and exiting while that blocked worker
  retains the lock. After the server releases, all three jobs complete successfully.
- Actual unavailable-video failure prevents worker launch and any HTTP request.
- Initial discovery and early/abrupt worker failure presentation without status-file writes.
- SDL-rendered frames at 640×480 and 320×240, measured long-title wrapping,
  event-injected B/Back/Escape exits, hotplug/resource cleanup and missing/stale JSON.
- Runtime UI smoke with Python `-S`: no third-party Python modules required.

Visual evidence in this execution session:

- `/tmp/ra-ports-live-progress.png`: actual installed launcher SDL capture while
  local fixture `snes / Game1` is fetching; **not live library data**.
- `/tmp/ra-progress-ui-fixture-320.png`: independently rendered secondary resolution,
  synthetic long title/retry values, visually inspected for clipping.

## Honest limits

No physical Batocera/Pi/Commodore 1702 execution, real controller connection,
KMS/DRM display handoff, overscan, live account or production library sync was
performed. The upstream Batocera 42 system definition supports `.sh` under Ports;
fullscreen SDL uses the desktop mode and a 640×480 logical canvas rather than
changing the CRT mode. Hardware validation is still needed.

This is a separate screen, **not** an integration with the native scraper dialog.
B/Back closes the screen but does not cancel sync. Mapped SDL controllers are
supported; unknown raw joystick buttons are not guessed. Latin-1 font glyphs are
bundled with license; unsupported scripts display `?`. A refresh processes mapped
unique RA game IDs, not every ROM file; duplicate ROM copies do not inflate totals.

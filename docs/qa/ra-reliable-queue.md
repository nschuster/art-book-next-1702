# Durable achievement refresh queue

## Scope

Helper-only update; no theme/layout, gamelist, ROM or Batocera login changes.
Saved positive `cheevosId` or explicit mappings remain necessary. Missing IDs and
ambiguous filename stems are diagnosed, not guessed.

## Verification

Executed locally: `python -m pytest tests -q`: **133 passed, 104 subtests passed**.
New queue tests cover overlapping CLI processes, priority, generation-safe ACK,
network recovery, killed in-flight worker recovery, account changes, stop/resume,
secret-free bounded logging, definition caching, malformed deadlines, startup
backoff preservation, and bounded retry exhaustion/forced renewal. Test API traffic
uses a real loopback HTTP server and synthetic fixtures, never a live RA account.

Independent managed-upgrade smoke passed: published `596c30d` installer to current
installer; repeated installation; installed manifest hashes; shell syntax; private
config bytes and permissions; unrelated hooks; uninstall. Data root contained spaces.

Observed RED: nonfinite queue deadlines and startup resetting retry backoff failed
before fixes. Bounded-watch test timed out before attempt limits were added, then
passed. Existing redirect test explicitly forces a new request because a normal
startup now correctly preserves the previous failure's deadline.

## Installation of the attached helper-only bundle

Extract `ra-helper-update.zip` into Batocera's network share root so it creates
`/userdata/ra-helper-update/`. No theme folder rename is required. Do not overwrite
the installed helper directly: its installer owns checksummed files.

Close games and stop the startup service if enabled. This command safely asks the
new helper to stop an active queue worker, then performs the managed upgrade:

```sh
python3 /userdata/ra-helper-update/sync.py --config /userdata/system/retroachievements/config.json --data-root /userdata --stop && python3 /userdata/ra-helper-update/install.py --data-root /userdata
```

Keep the existing config/login; do not rerun configure. Start a refresh:

```sh
python3 /userdata/system/retroachievements/sync.py --config /userdata/system/retroachievements/config.json --data-root /userdata --watch --force
```

For normal startup refresh, retain the existing enabled `ra-progress-sync` service.
The installer does not enable it automatically. Game-exit hooks are installed.
Default failure budget is three queue attempts, each with bounded HTTP retries.
Exhausted jobs remain pending until a new forced event/manual refresh renews them.

Inspect `/userdata/system/retroachievements/status.log` for `unmapped`, `retry`,
`rejected`, and `complete` events. Reselect the game after publication to reload extras.

## Evidence boundaries

No live API, Raspberry Pi, native display, or actual Batocera hook execution was
verified. Power loss between XML and ownership-manifest writes can still leave an
owned-file mismatch that is intentionally refused rather than overwritten; this
existing safety limitation is not a transactional filesystem guarantee. The worker
uses source stat changes to detect config/mapping changes, not a filesystem watcher.

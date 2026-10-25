#!/usr/bin/env python3
"""Short-lived, stdlib-only RetroAchievements -> Batocera per-game extras sync."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

API = 'https://retroachievements.org/API/'

class SyncError(Exception):
    pass

AUTH_HELP = 'In Batocera Game Settings > RetroAchievements, enable RA and reauthenticate your account, then sync again.'

def batocera_settings(root):
    """Read only the four allowed settings; ignore all other values without parsing."""
    prefix = 'global.retroachievements'
    allowed = {prefix, prefix + '.username', prefix + '.token', prefix + '.hardcore'}
    values = {}
    try:
        with (root / 'system/batocera.conf').open() as stream:
            for line in stream:
                separator = line.find('=')
                if separator < 0: continue
                key = line[:separator].strip()
                if key in allowed:
                    values[key] = line[separator + 1:].strip()
    except OSError:
        return {'username': '', 'token': '', 'enabled': True, 'mode': 'softcore'}
    return {'username': values.get(prefix + '.username', ''),
            'token': values.get(prefix + '.token', ''),
            'enabled': values.get(prefix, '0').lower() in ('1', 'true', 'on'),
            'mode': 'hardcore' if values.get(prefix + '.hardcore', '0').lower() in ('1', 'true', 'on') else 'softcore'}

def safe_path(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise SyncError('symlink output paths are not supported')
    return path

def atomic_write(path, data):
    path = safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.ra-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data); out.flush(); os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def load_config(path):
    st = path.stat()
    if path.is_symlink() or not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077 or st.st_uid != os.getuid():
        raise SyncError('config must be an owned regular file with mode 0600 (or 0400)')
    cfg = json.loads(path.read_text())
    if cfg.get('backend', 'webapi') not in ('batocera', 'webapi'):
        raise SyncError('invalid backend')
    if cfg.get('backend', 'webapi') == 'webapi' and (not cfg.get('username') or not cfg.get('api_key')):
        raise SyncError('username and api_key are required')
    if cfg.get('mode', 'hardcore') not in ('hardcore', 'softcore'):
        raise SyncError('mode must be hardcore or softcore')
    return cfg

def rom_key(system, rom, root):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', system):
        raise SyncError('invalid system name')
    if not isinstance(rom, str) or '\\' in rom or any(ord(c) < 32 for c in rom):
        raise SyncError('invalid ROM path')
    path = PurePosixPath(rom)
    if '..' in path.parts:
        raise SyncError('ROM path traversal is forbidden')
    if path.is_absolute():
        try: path = path.relative_to(root / 'roms' / system)
        except ValueError: raise SyncError('ROM path outside system') from None
    if not path.name or path.stem in ('', '.', '..'):
        raise SyncError('invalid ROM filename')
    return system, str(path)

def mappings(cfg, root, config_dir):
    result = {}
    known_roms = set()
    for system in cfg.get('systems', []):
        rom_key(system, 'validation.rom', root)
        gamelist = root / 'roms' / system / 'gamelist.xml'
        if not gamelist.exists(): continue
        for game in ET.parse(gamelist).getroot().findall('game'):
            known_roms.add(rom_key(system, game.findtext('path', ''), root))
            gid = game.findtext('cheevosId', '')
            if gid.isdecimal() and int(gid) > 0:
                result[rom_key(system, game.findtext('path', ''), root)] = int(gid)
    if cfg.get('mapping_file'):
        file = Path(cfg['mapping_file'])
        if not file.is_absolute(): file = config_dir / file
        for item in json.loads(file.read_text()):
            gid = item['game_id']
            if type(gid) is not int or gid <= 0:
                raise SyncError('game_id must be a positive integer')
            result[rom_key(item['system'], item['rom'], root)] = gid
    # ES addresses extras by stem, not ROM path. Include unmapped games so
    # their mapped neighbours cannot publish misleading shared progress.
    groups = {}
    for system, rom in known_roms | set(result):
        target = (system.casefold(), PurePosixPath(rom).stem.casefold())
        groups.setdefault(target, set()).add((system, rom))
    ambiguous = [games for games in groups.values() if len(games) > 1]
    skipped = set().union(*ambiguous) if ambiguous else set()
    if skipped:
        # Counts only: filenames, system names and credentials stay private.
        print(f'Warning: skipped {len(skipped)} games in {len(ambiguous)} ambiguous ROM stem groups; '
              'Batocera extras share a per-system filename stem. Unambiguous games continue; '
              'use distinct stems only for affected games to enable their progress.', file=sys.stderr)
    # Exclusion also invalidates previously owned extras during full reconciliation.
    return {key: gid for key, gid in result.items() if key not in skipped}

def progress(payload, gid):
    if not isinstance(payload, dict) or payload.get('ID') != gid:
        raise SyncError('invalid API game response')
    keys = ('NumAchievements', 'NumAwardedToUser', 'NumAwardedToUserHardcore')
    if any(type(payload.get(k)) is not int or payload[k] < 0 for k in keys):
        raise SyncError('invalid API achievement counts')
    if not 0 <= payload[keys[2]] <= payload[keys[1]] <= payload[keys[0]]:
        raise SyncError('inconsistent API achievement counts')
    return {k: payload[k] for k in ('ID', *keys)}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SyncError('API redirects refused')

class Client:
    def __init__(self, cfg, test_base):
        self.cfg = cfg
        self.base = API
        self.interval = max(1.0, min(60.0, float(cfg.get('min_interval', 1))))
        self.backoff = max(1.0, min(30.0, float(cfg.get('backoff', 2))))
        if test_base:
            url = urllib.parse.urlsplit(test_base)
            if url.scheme != 'http' or url.hostname not in ('127.0.0.1', 'localhost', '::1') or url.username or url.password or url.query or url.fragment:
                raise SyncError('test API must be an explicit loopback HTTP URL')
            self.base = test_base.rstrip('/') + '/'
            self.interval = max(0, self.interval if cfg.get('min_interval', 1) else 0)
            self.backoff = max(0, self.backoff if cfg.get('backoff', 2) else 0)
        self.last = 0
        self.opener = urllib.request.build_opener(NoRedirect)
    def fetch(self, gid):
        query = urllib.parse.urlencode({'y': self.cfg['api_key'], 'u': self.cfg['username'], 'g': gid})
        url = self.base + 'API_GetGameInfoAndUserProgress.php?' + query
        return progress(self.request(url), gid)

    def request(self, url, data=None):
        retries = max(0, min(4, int(self.cfg.get('retries', 2))))
        for attempt in range(retries + 1):
            time.sleep(max(0, self.last + self.interval - time.monotonic()))
            self.last = time.monotonic()
            try:
                req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Batocera-RA-Extras/1.0', 'Accept': 'application/json'})
                with self.opener.open(req, timeout=15) as response:
                    body = response.read(8 * 1024 * 1024 + 1)
                if len(body) > 8 * 1024 * 1024: raise SyncError('API response too large')
                return json.loads(body)
            except urllib.error.HTTPError as exc:
                if exc.code != 429 and exc.code < 500: break
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
            except (ValueError, SyncError):
                break
            if attempt < retries: time.sleep(min(30, self.backoff * 2 ** attempt))
        raise SyncError('API unavailable or invalid response; existing cache retained')

class TokenClient(Client):
    def __init__(self, cfg, test_base):
        super().__init__(cfg, test_base)
        self.endpoint = self.base + 'dorequest.php' if test_base else 'https://retroachievements.org/dorequest.php'

    def call(self, operation, gid, **fields):
        body = urllib.parse.urlencode(dict(r=operation, u=self.cfg['username'], t=self.cfg['token'], g=gid, **fields)).encode()
        payload = self.request(self.endpoint, body)
        if not isinstance(payload, dict) or payload.get('Success') is not True:
            raise SyncError('invalid client API response')
        return payload

    def fetch(self, gid):
        def valid_id(value):
            return type(value) is int and 0 < value <= 0xffffffff
        if not valid_id(gid): raise SyncError('invalid game ID')
        patch = self.call('patch', gid).get('PatchData')
        if not isinstance(patch, dict) or not valid_id(patch.get('ID')) or patch['ID'] != gid or not isinstance(patch.get('Achievements'), list):
            raise SyncError('invalid patch')
        core = set()
        for achievement in patch['Achievements']:
            if not isinstance(achievement, dict) or not valid_id(achievement.get('ID')) or type(achievement.get('Flags')) is not int or not 0 <= achievement['Flags'] <= 0xffffffff:
                raise SyncError('invalid achievement')
            if achievement['Flags'] == 3: core.add(achievement['ID'])
        modes = []
        for mode in (0, 1):
            unlocked = self.call('unlocks', gid, h=mode).get('UserUnlocks')
            if not isinstance(unlocked, list) or any(not valid_id(value) for value in unlocked):
                raise SyncError('invalid unlocks')
            modes.append(core.intersection(unlocked))
        return progress({'ID': gid, 'NumAchievements': len(core),
                         'NumAwardedToUser': len(modes[0] | modes[1]),
                         'NumAwardedToUserHardcore': len(modes[1])}, gid)

def progress_asset(data, cfg, root):
    """Exact vector fill; the complete smooth rainbow spans the unlocked fill."""
    key = 'NumAwardedToUserHardcore' if cfg.get('mode', 'hardcore') == 'hardcore' else 'NumAwardedToUser'
    total = data['NumAchievements']
    width = 1000 * data[key] / total if total else 0
    stops = ''.join(f'<stop offset="{offset}%" stop-color="{color}"/>' for offset, color in
                    [(0, '#cf493e'), (25, '#df8c38'), (50, '#e4c653'), (75, '#6b9b62'), (100, '#527eb0')])
    content = (f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="85.9375" viewBox="0 0 1000 85.9375" preserveAspectRatio="none">'
               f'<defs><linearGradient id="rainbow" x1="0%" y1="0%" x2="100%" y2="0%">{stops}</linearGradient></defs>'
               f'<rect id="fill" width="{width:.15g}" height="85.9375" fill="url(#rainbow)"/></svg>').encode()
    digest = hashlib.sha256(content).hexdigest()
    return Path(root).absolute() / 'system/retroachievements/assets' / (digest + '.svg'), content


def track_asset(root):
    """White tint source: current palette is resolved by ES, never baked into cache."""
    content = b'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="85.9375" viewBox="0 0 1000 85.9375" preserveAspectRatio="none"><rect width="1000" height="85.9375" fill="#ffffff"/></svg>'
    digest = hashlib.sha256(content).hexdigest()
    return Path(root).absolute() / 'system/retroachievements/assets' / (digest + '.svg'), content


def trophy_asset(root):
    """Exact U+F091 outline, uniformly scaled without font-size quantization.

    FontTools SVGPathPen extraction from pinned Batocera FontAwesome 4.3.0;
    source SHA256 9e540a087924a6e64790149d735cac022640e4fa6bff6bd65f5e9f41529bf0b3.
    Bounds (0,-128,1664,1408), centered in a square, not stretched/cropped.
    Copyright Dave Gandy 2015, SIL OFL 1.1: tools/assets/OFL-1.1.txt.
    No FontTools or font installation is needed on the device.
    """
    content = b'<svg xmlns="http://www.w3.org/2000/svg" width="1664" height="1664" viewBox="0 0 1664 1664"><!-- Exact U+F091: FontAwesome 4.3.0, Copyright Dave Gandy 2015, SIL OFL 1.1 https://openfontlicense.org/open-font-license-official-text/ . Source: Batocera ES 4adf26b43900d1a33887af6d8af3da2e99e398a5 resources/fontawesome-webfont.ttf --><path fill="#ffffff" transform="translate(0 1472) scale(1 -1)" d="M458 653Q384 815 384 1024H128V928Q128 850 222.5 766.0Q317 682 458 653ZM1536 928V1024H1280Q1280 815 1206 653Q1347 682 1441.5 766.0Q1536 850 1536 928ZM1664 1056V928Q1664 857 1622.5 785.0Q1581 713 1510.5 655.0Q1440 597 1337.5 557.5Q1235 518 1122 513Q1080 459 1027 418Q989 384 974.5 345.5Q960 307 960 256Q960 202 990.5 165.0Q1021 128 1088 128Q1163 128 1221.5 82.5Q1280 37 1280 -32V-96Q1280 -110 1271.0 -119.0Q1262 -128 1248 -128H416Q402 -128 393.0 -119.0Q384 -110 384 -96V-32Q384 37 442.5 82.5Q501 128 576 128Q643 128 673.5 165.0Q704 202 704 256Q704 307 689.5 345.5Q675 384 637 418Q584 459 542 513Q429 518 326.5 557.5Q224 597 153.5 655.0Q83 713 41.5 785.0Q0 857 0 928V1056Q0 1096 28.0 1124.0Q56 1152 96 1152H384V1248Q384 1314 431.0 1361.0Q478 1408 544 1408H1120Q1186 1408 1233.0 1361.0Q1280 1314 1280 1248V1152H1568Q1608 1152 1636.0 1124.0Q1664 1096 1664 1056Z"/></svg>'
    digest = hashlib.sha256(content).hexdigest()
    return Path(root).absolute() / 'system/retroachievements/assets' / (digest + '.svg'), content


def store_asset(state, path, content):
    """Journal ownership before writing, so interrupted writes can be collected."""
    path = safe_path(path)
    registry = safe_path(state / 'assets-manifest.json')
    owned = json.loads(registry.read_text()) if registry.exists() else {}
    digest = hashlib.sha256(content).hexdigest()
    if path.exists() and (owned.get(path.name) != digest or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
        raise SyncError('refusing unmanaged or changed progress asset')
    owned[path.name] = digest
    atomic_write(registry, json.dumps(owned).encode())
    if not path.exists(): atomic_write(path, content)


def collect_assets(state, extras):
    """Keep referenced assets; never delete unowned or locally changed files."""
    registry = safe_path(state / 'assets-manifest.json')
    if not registry.exists(): return
    owned = json.loads(registry.read_text())
    references = set()
    for relative, entry in extras.items():
        path = safe_path(state / 'extras' / relative)
        if not path.exists(): continue
        content = path.read_bytes()
        # A local edit may add references: defer GC rather than guess ownership.
        if hashlib.sha256(content).hexdigest() != entry.get('sha256'): return
        references.update(n.text for n in ET.fromstring(content).findall('./view/image/path'))
    for name, digest in list(owned.items()):
        if not re.fullmatch(r'[0-9a-f]{64}\.svg', name) or name != digest + '.svg':
            raise SyncError('invalid owned asset manifest')
        path = safe_path(state / 'assets' / name)
        if str(path) in references: continue
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest: continue
            path.unlink()
        del owned[name]
    atomic_write(registry, json.dumps(owned).encode())


def render(data, cfg, root):
    template = cfg.get('template', {})
    font = template.get('fontPath', '${themePath}/${fontBold}')
    if font != '${themePath}/${fontBold}' and not Path(font).is_absolute(): raise SyncError('fontPath must be absolute')
    theme = ET.Element('theme'); ET.SubElement(theme, 'formatVersion').text = '7'
    view = ET.SubElement(theme, 'view', name='detailed,video')
    text = ET.SubElement(view, 'text', name='ra_progress', extra='true')
    key = 'NumAwardedToUserHardcore' if cfg.get('mode', 'hardcore') == 'hardcore' else 'NumAwardedToUser'
    props = {'pos': '0.76953125 0.837916666666667', 'size': '0.14 0.045833333333333', 'fontPath': font,
             'fontSize': '0.027777777777777', 'color': '${gamelistListTextlistUnselectedColor}', 'alignment': 'center',
             'origin': '0.5 0.5', 'multiLine': 'false',
             'verticalAlignment': 'center', 'zIndex': '101', 'visible': 'true'}
    for keyname in props:
        ET.SubElement(text, keyname).text = str(template.get(keyname, props[keyname]))
    label = template.get('label', '')
    ET.SubElement(text, 'text').text = f"{label + ' ' if label else ''}{data[key]}/{data['NumAchievements']}"
    image = ET.SubElement(view, 'image', name='ra_progress_bar', extra='true')
    asset, _ = progress_asset(data, cfg, root)
    for name, value in {'pos': '0.5890625 0.815', 'size': '0.3609375 0.045833333333333', 'origin': '0 0',
                        'path': str(asset), 'color': 'FFFFFFFF', 'zIndex': '100', 'visible': 'true'}.items():
        ET.SubElement(image, name).text = value
    track = ET.SubElement(view, 'image', name='ra_progress_track', extra='true')
    for name, value in {'pos': '0.5890625 0.815', 'size': '0.3609375 0.045833333333333', 'origin': '0 0',
                        'path': str(track_asset(root)[0]), 'color': '${raProgressTrackColor}',
                        'zIndex': '99', 'visible': 'true'}.items():
        ET.SubElement(track, name).text = value
    # Exact CHEEVOSICON outline, metadata only; native game-name font is untouched.
    # Move the enlarged ink left, not the bar, retaining optical 6px/3px gaps.
    trophy = ET.SubElement(view, 'image', name='ra_progress_trophy', extra='true')
    for name, value in {'pos': '0.548 0.837916666666667', 'size': '0.03125 0.041666666666667',
                        'origin': '0 0.5', 'path': str(trophy_asset(root)[0]),
                        'color': '${gamelistListMetadataIconColor}',
                        'zIndex': '101', 'visible': 'true'}.items():
        ET.SubElement(trophy, name).text = value
    return ET.tostring(theme, encoding='utf-8', xml_declaration=True)

def run(args):
    cfg_path = Path(args.config).absolute()
    cfg = load_config(cfg_path)
    root = Path(args.data_root).absolute()
    native = cfg.get('backend') == 'batocera'
    if native: cfg.update(batocera_settings(root))
    inactive = native and (not cfg['enabled'] or not cfg['username'] or not cfg['token'])
    records = mappings(cfg, root, cfg_path.parent)
    if inactive: records = {}
    all_records = dict(records)
    if args.rom and not args.system:
        raise SyncError('--rom requires --system')
    if args.system:
        if args.rom:
            selected = rom_key(args.system, args.rom, root)
            records = {key: gid for key, gid in records.items() if key == selected}
        else:
            records = {key: gid for key, gid in records.items() if key[0] == args.system}
    state = safe_path(root / 'system/retroachievements')
    state.mkdir(parents=True, exist_ok=True)
    targets = {key: safe_path(state / 'extras' / key[0] / (PurePosixPath(key[1]).stem + '.xml')) for key in records}
    lock_path = safe_path(state / 'sync.lock')
    with lock_path.open('a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Sync already running; skipped.'); return 0
        client = (TokenClient if native else Client)(cfg, args.test_api_base)
        # SHA256 namespaces account caches, never hashes ROMs.
        account = hashlib.sha256(cfg['username'].encode()).hexdigest()[:24]
        manifest = safe_path(state / 'extras-manifest.json')
        owned = json.loads(manifest.read_text()) if manifest.exists() else {}
        desired = {
            str(Path(system) / (PurePosixPath(rom).stem + '.xml')):
                {'account': account, 'mode': cfg.get('mode', 'hardcore'), 'rom': rom, 'game_id': gid}
            for (system, rom), gid in all_records.items()
        }
        # Reconcile against the FULL mapping, even on a targeted refresh. Account,
        # game ID and mode changes must not masquerade as valid offline progress.
        for relative, entry in list(owned.items()):
            parts = PurePosixPath(relative).parts
            if len(parts) != 2 or '..' in parts or PurePosixPath(relative).is_absolute() or not relative.endswith('.xml'):
                raise SyncError('invalid owned extras manifest')
            path = safe_path(state / 'extras' / relative)
            if entry.get('identity') != desired.get(relative):
                if path.exists():
                    if hashlib.sha256(path.read_bytes()).hexdigest() != entry.get('sha256'):
                        raise SyncError('locally changed extra cannot be safely pruned')
                    path.unlink()
                del owned[relative]
        atomic_write(manifest, json.dumps(owned).encode())
        if inactive:
            collect_assets(state, owned)
            if cfg['enabled']:
                print(AUTH_HELP, file=sys.stderr)
                return 2
            print('Batocera RA is disabled; owned progress extras removed. Reload the game list to clear an already displayed panel.')
            return 0
        failures = 0; fetched = {}; count = 0
        for key, gid in records.items():
            cache = safe_path(state / 'cache' / ('batocera' if native else 'webapi') / account / (str(gid) + '.json'))
            try:
                if gid in fetched and fetched[gid] is None:
                    raise SyncError('game already failed this run')
                if gid not in fetched:
                    fetched[gid] = None
                    data = None
                    if not args.force and cache.exists() and time.time() - cache.stat().st_mtime < max(0, float(cfg.get('cache_ttl', 900))):
                        try: data = progress(json.loads(cache.read_text()), gid)
                        except (ValueError, SyncError): pass
                    if data is None:
                        data = client.fetch(gid)
                        atomic_write(cache, json.dumps(data).encode())
                    fetched[gid] = data
                target = targets[key]
                relative = str(target.relative_to(state / 'extras'))
                if target.exists():
                    previous = owned.get(relative)
                    if not previous or hashlib.sha256(target.read_bytes()).hexdigest() != previous.get('sha256'):
                        raise SyncError('refusing unmanaged or changed progress extra')
                asset, asset_content = progress_asset(fetched[gid], cfg, root)
                store_asset(state, asset, asset_content)
                track, track_content = track_asset(root)
                store_asset(state, track, track_content)
                trophy, trophy_content = trophy_asset(root)
                store_asset(state, trophy, trophy_content)
                content = render(fetched[gid], cfg, root)
                atomic_write(target, content)
                owned[relative] = {'identity': desired[relative], 'sha256': hashlib.sha256(content).hexdigest()}
                atomic_write(manifest, json.dumps(owned).encode())
                count += 1
            except (SyncError, OSError):
                failures += 1
                print('Game sync failed; existing files retained.', file=sys.stderr)
                if native: print(AUTH_HELP, file=sys.stderr)
        collect_assets(state, owned)
        print(f'Sync complete: {count} extras written, {failures} failures.')
        return 1 if failures else 0

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--data-root', default='/userdata')
    parser.add_argument('--system', help='only this system')
    parser.add_argument('--rom', help='only this ROM (requires --system)')
    parser.add_argument('--force', action='store_true', help='refresh even if cache is fresh')
    parser.add_argument('--test-api-base', help='TEST ONLY: loopback HTTP mock API; never a live-success claim')
    args = parser.parse_args()
    try: return run(args)
    except (SyncError, OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
        # Never print exception details: upstream URLs and JSON may contain secrets.
        print('Sync rejected configuration, mapping, or filesystem; check private config, safe paths and permissions. If owned extras were modified, restore them or disable the theme RA display; modified files cannot be safely removed.', file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())

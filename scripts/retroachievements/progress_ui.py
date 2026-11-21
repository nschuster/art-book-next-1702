#!/usr/bin/env python3
"""Read-only RA progress window. Runtime: Python stdlib, SDL2, ui-assets/.

run_ui initializes every display resource before start_callback() exactly once.
It never starts/stops a worker itself. Closing this window leaves sync running.
Unmapped joystick buttons are ignored unless raw_back_button is explicitly set.
"""
import argparse
import ctypes as C
import ctypes.util
from datetime import datetime
import json
import math
from pathlib import Path
import struct
import sys
import time
import unicodedata
from ui_palette import load_palette

ASSETS = Path(__file__).resolve().parent / 'ui-assets'
WIDTHS = json.loads((ASSETS / 'widths.json').read_text())
SAFE_ERROR = 'RA progress UI unavailable (SDL/display/resources). Sync was not started by this UI.'
STATES = {'starting': 'Starting sync', 'scanning': 'Scanning library',
          'syncing': 'Syncing achievements', 'retrying': 'Retrying request',
          'complete': 'Sync complete', 'failed': 'Sync failed',
          'stopped': 'Sync stopped', 'disabled': 'Achievements disabled'}


def clean(value):
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        return ''
    text = unicodedata.normalize('NFKC', str(value))[:2048]
    text = text.translate(str.maketrans({'’': "'", '‘': "'", '“': '"', '”': '"', '–': '-', '—': '-'}))
    text = ''.join(ch if 32 <= ord(ch) <= 255 and not unicodedata.category(ch).startswith('C') else ' ' if ch.isspace() else '?' for ch in text)
    return ' '.join(text.split())


def text_width(text, scale=1):
    return sum(WIDTHS.get(str(ord(ch)), WIDTHS['63']) for ch in text) * scale


def ellipsis(text, width, scale=1):
    text = clean(text)
    if text_width(text, scale) <= width:
        return text
    while text and text_width(text + '...', scale) > width:
        text = text[:-1]
    return text.rstrip() + '...'


def wrap(text, width=576, lines=2):
    words = clean(text).split()
    result = []
    while words and len(result) < lines - 1:
        line = words.pop(0)
        while words and text_width(line + ' ' + words[0]) <= width:
            line += ' ' + words.pop(0)
        result.append(ellipsis(line, width))
    if words:
        result.append(ellipsis(' '.join(words), width))
    return result or ['Waiting for game...']


def read_status(path):
    try:
        with Path(path).open('r', encoding='utf-8') as source:
            return json.loads(source.read(65537))
    except (OSError, ValueError, UnicodeError):
        return None


def build_model(status, now=None, stale_after=180):
    m = dict(title='Waiting for sync status', system='No current console', game='No current game',
             fraction=None, summary='Progress unavailable', detail='Waiting for worker update', state='unknown')
    if (not isinstance(status, dict) or type(status.get('schema')) is not int
            or status.get('schema') != 1 or not isinstance(status.get('state'), str)
            or status['state'] not in STATES):
        return m
    for key in ('total', 'completed', 'failed', 'updated', 'cached', 'pending', 'attempt'):
        value = status.get(key, 0)
        if type(value) is not int or value < 0:
            return m
    try:
        stamp = status['updated_at']
        if isinstance(stamp, bool):
            return m
        stamp = datetime.fromisoformat(stamp.replace('Z', '+00:00')).timestamp() if isinstance(stamp, str) else float(stamp)
        age = (time.time() if now is None else now) - stamp
        if not math.isfinite(age) or age < -60 or age > stale_after:
            m.update(title='Status is stale', detail='Worker activity is not confirmed')
            return m
    except (KeyError, TypeError, ValueError, OverflowError):
        return m
    state = status['state']
    def count(key):
        value = status.get(key, 0)
        return min(value, 999999999) if type(value) is int and value >= 0 else 0
    total, completed, failed = count('total'), count('completed'), count('failed')
    m.update(title=STATES[state], state=state,
             system=clean(status.get('system') or status.get('system_id')) or 'No current console',
             game=clean(status.get('game') or status.get('rom_stem')) or 'No current game')
    if state == 'complete' and failed:
        m['title'] = 'Finished with failures'
    m['summary'] = f'{completed} succeeded / {total} games'
    m['detail'] = f"{count('updated')} updated   {count('cached')} cached   {failed} failed"
    if state == 'retrying':
        m['detail'] = f"Retry: job {count('attempt')} / HTTP {count('request_attempt')}"
    if total and state not in ('starting', 'scanning', 'disabled'):
        m['fraction'] = min(1.0, (completed + failed) / total)
    if state in ('starting', 'scanning'):
        m['summary'] = 'Counting unique mapped games...'
    m['pending'] = count('pending')
    return m


def layout(model):
    """Fixed baselines and measured glyph advances: 32px safe margins."""
    result = [(32, 28, 'RETROACHIEVEMENTS', 1.0),
              (32, 82, ellipsis(model['title'], 576), 1.0),
              (32, 130, ellipsis(model['system'], 576), 1.0)]
    for i, line in enumerate(wrap(model['game'])):
        result.append((32, 166 + i*30, line, 1.0))
    result.extend([(32, 246, ellipsis(model['summary'], 576), 1.0),
                   (32, 316, ellipsis(model['detail'], 576), 1.0),
                   (32, 350, ellipsis('Pending: ' + str(model['pending']) if 'pending' in model else 'No completion assumed', 576), 1.0),
                   (32, 388, 'B / Back / Esc  -  Return', 1.0),
                   (32, 418, 'Closing this screen does not stop sync.', 1.0)])
    return result


class Rect(C.Structure):
    _fields_ = [('x', C.c_int), ('y', C.c_int), ('w', C.c_int), ('h', C.c_int)]


class Event(C.Union):
    _fields_ = [('type', C.c_uint32), ('padding', C.c_uint8 * 56), ('align', C.c_uint64)]


def event(kind, key=0, button=0):
    ev = Event(); ev.type = kind
    if kind == 0x300:
        C.c_int32.from_buffer(ev, 20).value = key
    else:
        ev.padding[12] = button
    return ev


def should_quit(ev, raw_back_button=None):
    return (ev.type == 0x100 or
            ev.type == 0x300 and C.c_int32.from_buffer(ev, 20).value == 27 or
            ev.type == 0x651 and ev.padding[12] in (1, 4) or
            ev.type == 0x603 and raw_back_button is not None and ev.padding[12] == raw_back_button)


def load_sdl():
    name = ctypes.util.find_library('SDL2') or 'libSDL2-2.0.so.0'
    lib = C.CDLL(name)
    ptr, integer = C.c_void_p, C.c_int
    signatures = {
        'SDL_InitSubSystem': (integer, [C.c_uint32]), 'SDL_QuitSubSystem': (None, [C.c_uint32]),
        'SDL_SetHint': (integer, [C.c_char_p, C.c_char_p]),
        'SDL_CreateWindow': (ptr, [C.c_char_p, integer, integer, integer, integer, C.c_uint32]),
        'SDL_DestroyWindow': (None, [ptr]), 'SDL_CreateRenderer': (ptr, [ptr, integer, C.c_uint32]),
        'SDL_DestroyRenderer': (None, [ptr]), 'SDL_RenderSetLogicalSize': (integer, [ptr, integer, integer]),
        'SDL_SetRenderDrawColor': (integer, [ptr, C.c_uint8, C.c_uint8, C.c_uint8, C.c_uint8]),
        'SDL_RenderClear': (integer, [ptr]), 'SDL_RenderFillRect': (integer, [ptr, C.POINTER(Rect)]),
        'SDL_RenderPresent': (None, [ptr]), 'SDL_PollEvent': (integer, [C.POINTER(Event)]),
        'SDL_PushEvent': (integer, [C.POINTER(Event)]), 'SDL_Delay': (None, [C.c_uint32]),
        'SDL_RWFromFile': (ptr, [C.c_char_p, C.c_char_p]), 'SDL_LoadBMP_RW': (ptr, [ptr, integer]),
        'SDL_SetColorKey': (integer, [ptr, integer, C.c_uint32]), 'SDL_FreeSurface': (None, [ptr]),
        'SDL_CreateTextureFromSurface': (ptr, [ptr, ptr]), 'SDL_DestroyTexture': (None, [ptr]),
        'SDL_SetTextureColorMod': (integer, [ptr, C.c_uint8, C.c_uint8, C.c_uint8]),
        'SDL_RenderCopy': (integer, [ptr, ptr, C.POINTER(Rect), C.POINTER(Rect)]),
        'SDL_GetRendererOutputSize': (integer, [ptr, C.POINTER(integer), C.POINTER(integer)]),
        'SDL_RenderReadPixels': (integer, [ptr, ptr, C.c_uint32, ptr, integer]),
        'SDL_NumJoysticks': (integer, []), 'SDL_IsGameController': (integer, [integer]),
        'SDL_GameControllerOpen': (ptr, [integer]), 'SDL_GameControllerClose': (None, [ptr]),
        'SDL_JoystickOpen': (ptr, [integer]), 'SDL_JoystickClose': (None, [ptr]),
        'SDL_GameControllerGetJoystick': (ptr, [ptr]), 'SDL_JoystickInstanceID': (integer, [ptr]),
        'SDL_ShowCursor': (integer, [integer]),
    }
    for name, (restype, argtypes) in signatures.items():
        fn = getattr(lib, name); fn.restype = restype; fn.argtypes = argtypes
    return lib


def save_bmp(lib, renderer, path):
    w, h = C.c_int(), C.c_int()
    if lib.SDL_GetRendererOutputSize(renderer, C.byref(w), C.byref(h)):
        raise RuntimeError('capture')
    # SDL_PIXELFORMAT_ARGB8888: little-endian bytes B,G,R,A; BMP is bottom-up BGRA.
    pixels = (C.c_uint8 * (w.value*h.value*4))()
    if lib.SDL_RenderReadPixels(renderer, None, 372645892, pixels, w.value*4):
        raise RuntimeError('capture')
    raw = bytes(pixels); pitch = w.value*4
    header = struct.pack('<2sIHHI', b'BM', 54+len(raw), 0, 0, 54)
    header += struct.pack('<IiiHHIIiiII', 40, w.value, h.value, 1, 32, 0, len(raw), 2835, 2835, 0, 0)
    with Path(path).open('wb') as out:
        out.write(header)
        for row in range(h.value-1, -1, -1):
            out.write(raw[row*pitch:(row+1)*pitch])


def run_ui(state_path, start_callback=None, *, fullscreen=True, size=(640, 480),
           frames=None, screenshot=None, stale_after=180, raw_back_button=None, status_reader=None,
           screen=None, data_root=None):
    """Initialize first, callback second, read-only poll last. Return 0 or safe 2.

    fullscreen uses SDL_WINDOW_FULLSCREEN_DESKTOP: never changes display mode.
    SDL logical size letterboxes to 4:3. Status is sampled at 5Hz; events at 25Hz.
    """
    lib = None; window = renderer = texture = None
    devices = {}; initialized = False; started = False; cursor = None
    flags = 0x20 | 0x200 | 0x2000  # VIDEO, JOYSTICK, GAMECONTROLLER
    try:
        root = Path(data_root) if data_root is not None else (Path(state_path).absolute().parents[2] if state_path is not None and len(Path(state_path).absolute().parents) > 2 else Path('/userdata'))
        palette = load_palette(root)
        lib = load_sdl()
        if lib.SDL_InitSubSystem(flags):
            raise RuntimeError('init')
        initialized = True
        lib.SDL_SetHint(b'SDL_RENDER_SCALE_QUALITY', b'0')
        window = lib.SDL_CreateWindow(b'RetroAchievements sync', 0x2FFF0000, 0x2FFF0000,
                                      size[0], size[1], 0x1001 if fullscreen else 4)
        if not window:
            raise RuntimeError('window')
        renderer = lib.SDL_CreateRenderer(window, -1, 0)
        if not renderer or lib.SDL_RenderSetLogicalSize(renderer, 640, 480):
            raise RuntimeError('renderer')
        rw = lib.SDL_RWFromFile(str(ASSETS / 'font.bmp').encode(), b'rb')
        surface = lib.SDL_LoadBMP_RW(rw, 1) if rw else None
        if not surface:
            raise RuntimeError('font')
        try:
            if lib.SDL_SetColorKey(surface, 1, 0xFF00FF):
                raise RuntimeError('font')
            texture = lib.SDL_CreateTextureFromSurface(renderer, surface)
        finally:
            lib.SDL_FreeSurface(surface)
        if not texture:
            raise RuntimeError('texture')
        if lib.SDL_SetTextureColorMod(texture, *palette['text']):
            raise RuntimeError('font tint')
        def open_device(index):
            mapped = bool(lib.SDL_IsGameController(index))
            handle = lib.SDL_GameControllerOpen(index) if mapped else lib.SDL_JoystickOpen(index)
            if handle:
                joy = lib.SDL_GameControllerGetJoystick(handle) if mapped else handle
                instance = lib.SDL_JoystickInstanceID(joy)
                if instance in devices:
                    (lib.SDL_GameControllerClose if mapped else lib.SDL_JoystickClose)(handle)
                else:
                    devices[instance] = (handle, mapped)
        for index in range(lib.SDL_NumJoysticks()):
            open_device(index)
        cursor = lib.SDL_ShowCursor(0)
        started = True  # Callback may launch successfully and then raise.
        if start_callback is not None:
            start_callback()
        frame = 0; next_read = 0; model = build_model(None)
        def fill(x, y, w, h, color):
            lib.SDL_SetRenderDrawColor(renderer, *color, 255)
            rect = Rect(x, y, w, h)
            lib.SDL_RenderFillRect(renderer, C.byref(rect))
        while frames is None or frame < frames:
            ev = Event()
            while lib.SDL_PollEvent(C.byref(ev)):
                # Ignore raw events from already-mapped controllers.
                instance = C.c_int32.from_buffer(ev, 8).value
                raw = raw_back_button if not devices.get(instance, (None, False))[1] else None
                if should_quit(ev, raw):
                    return 0
                if screen is not None:
                    screen.handle_event(ev)
                if ev.type == 0x605:  # JOYDEVICEADDED (device index)
                    open_device(instance)
                elif ev.type == 0x606 and instance in devices:
                    handle, mapped = devices.pop(instance)
                    (lib.SDL_GameControllerClose if mapped else lib.SDL_JoystickClose)(handle)
            now = time.monotonic()
            if screen is None and now >= next_read:
                model = build_model(status_reader() if status_reader is not None else read_status(state_path), stale_after=stale_after)
                next_read = now + .2
            lib.SDL_SetRenderDrawColor(renderer, *palette['background'], 255)
            lib.SDL_RenderClear(renderer)
            fill(32, 67, 576, 3, palette['divider'])
            colors = [(167,69,57), (190,119,62), (197,169,78), (108,145,105), (77,119,151)]
            for i, color in enumerate(colors):
                fill(488+i*24, 39, 24, 8, color)
            if screen is None:
                fill(32, 288, 576, 16, palette['track'])
                if model['fraction'] is not None:
                    fill(32, 288, round(576*model['fraction']), 16, palette['progress'])
            for x, y, text, scale in (screen.layout() if screen is not None else layout(model)):
                pen = float(x)
                for ch in text:
                    code = ord(ch) if 32 <= ord(ch) <= 255 else 63
                    src = Rect(((code-32)%16)*32, ((code-32)//16)*32, WIDTHS[str(code)], 30)
                    dest = Rect(round(pen), y, max(1, round(src.w*scale)), round(30*scale))
                    lib.SDL_RenderCopy(renderer, texture, C.byref(src), C.byref(dest))
                    pen += src.w*scale
            if screenshot is not None and (frames is None or frame == frames-1):
                save_bmp(lib, renderer, screenshot)
                screenshot = None
            lib.SDL_RenderPresent(renderer)
            frame += 1
            lib.SDL_Delay(40)
        return 0
    except Exception:
        print('RA progress UI unavailable; sync may continue in the background.' if started else SAFE_ERROR, file=sys.stderr)
        return 2
    finally:
        if lib is not None:
            for handle, mapped in devices.values():
                (lib.SDL_GameControllerClose if mapped else lib.SDL_JoystickClose)(handle)
            if texture: lib.SDL_DestroyTexture(texture)
            if renderer: lib.SDL_DestroyRenderer(renderer)
            if window: lib.SDL_DestroyWindow(window)
            if cursor is not None: lib.SDL_ShowCursor(cursor)
            if initialized: lib.SDL_QuitSubSystem(flags)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=Path('/userdata/system/retroachievements'))
    parser.add_argument('--state-path', type=Path)
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--width', type=int, default=640)
    parser.add_argument('--height', type=int, default=480)
    parser.add_argument('--frames', type=int)
    parser.add_argument('--screenshot', type=Path)
    parser.add_argument('--raw-back-button', type=int, help='Explicit zero-based button for unmapped joysticks; disabled by default')
    args = parser.parse_args(argv)
    if args.width < 160 or args.height < 120 or (args.frames is not None and args.frames < 1):
        parser.error('positive frames and size >=160x120 required')
    return run_ui(args.state_path or args.data_root / 'progress.json', fullscreen=not args.windowed,
                  size=(args.width, args.height), frames=args.frames, screenshot=args.screenshot,
                  raw_back_button=args.raw_back_button)


if __name__ == '__main__':
    sys.exit(main())

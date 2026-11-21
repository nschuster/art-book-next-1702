from test_ra_palette_ui import fixture
import progress_ui


def test_current_palette_wins_over_stale_theme_snapshot(tmp_path):
    root, es, theme = fixture(tmp_path, 'commodore-64', current='snes')
    # Current settings say SNES; saved previous-visit theme snapshot says C64.
    assert progress_ui.load_palette(root)['background'] == (20, 14, 38)
    # An unreadable old snapshot must not invalidate a valid current choice.
    (es/'themesettings/renamed.cfg').write_bytes(b'\xff')
    assert progress_ui.load_palette(root)['background'] == (20, 14, 38)


def contrast(a, b):
    def luminance(rgb):
        values = [v / 255 for v in rgb]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(v*w for v,w in zip(linear, (.2126,.7152,.0722)))
    x,y=sorted((luminance(a),luminance(b)))
    return (y+.05)/(x+.05)


def test_light_palette_progress_has_contrast_on_menu_surface(tmp_path):
    root, es, theme = fixture(tmp_path, 'light')
    (es/'es_settings.cfg').write_text('<config><string name="ThemeSet" value="renamed"/></config>')
    palette = progress_ui.load_palette(root)
    assert contrast(palette['progress'], palette['background']) >= 3
    assert contrast(palette['progress'], palette['track']) >= 3

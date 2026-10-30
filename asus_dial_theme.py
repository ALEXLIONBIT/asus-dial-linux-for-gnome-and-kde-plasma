"""Drawing of the ASUS Dial radial menu and on-screen messages, with themes.

Used by the driver (asus-dial) for the real thing and by asus-dial-manager for the live preview,
so what you see in the settings app is what you get on the dial.

Themes (see asus_dial_config.DEFAULT_THEME): plain color, image, rainbow, Halloween, Christmas and Plasma
backgrounds, plus blur (frosted glass), glow, glossy reflection, shadow and sparkles.
"""
import colorsys
import configparser
import math
import os
import random
import time

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango, PangoCairo
import cairo

MENU_PAD, MENU_PAD_HALLOWEEN = 50, 110
THEMED = ("halloween", "christmas")  # backgrounds with their own artwork around the menu and the messages
OSD_W, OSD_H, OSD_PAD, OSD_PAD_HALLOWEEN = 360, 110, 30, 56


# ------------------------------------------------------------------ helpers
def rgb(hex_color, default=(0.5, 0.5, 0.5)):
    h = (hex_color or "").lstrip("#")
    try:
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return default


# ------------------------------------------------------------------ Plasma theme: the colors of the desktop
# Breeze's own colors, for when the desktop tells only "light" or "dark" (GNOME, or a forced style on Plasma)
BREEZE = {"dark": {"bg": (0.125, 0.137, 0.149), "view": (0.078, 0.086, 0.094), "fg": (0.988, 0.988, 0.988)},
          "light": {"bg": (0.937, 0.941, 0.945), "view": (0.988, 0.988, 0.988), "fg": (0.137, 0.149, 0.161)}}
BREEZE_ACCENT = (0.239, 0.682, 0.914)
KDEGLOBALS = os.path.expanduser("~/.config/kdeglobals")
_system_look = {"t": -10.0, "mtime": None, "look": None}


def _kde_color(cfg, section, key):
    try:
        r, g, b = (int(v) for v in cfg.get(section, key).split(",")[:3])
        return r / 255, g / 255, b / 255
    except (configparser.Error, ValueError):
        return None


def _luma(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _read_system_look():
    """{"dark": bool, "accent": rgb, "scheme": {bg, view, fg} or None} of the running desktop."""
    if "kde" in os.environ.get("XDG_CURRENT_DESKTOP", "").lower() and os.path.exists(KDEGLOBALS):
        cfg = configparser.ConfigParser(interpolation=None, strict=False)
        cfg.optionxform = str
        try:
            cfg.read(KDEGLOBALS)
        except configparser.Error:
            cfg = None
        if cfg is not None:
            bg, view, fg = (_kde_color(cfg, f"Colors:{s}", k) for s, k in
                            (("Window", "BackgroundNormal"), ("View", "BackgroundNormal"), ("Window", "ForegroundNormal")))
            accent = _kde_color(cfg, "General", "AccentColor") or _kde_color(cfg, "Colors:Selection", "BackgroundNormal")
            if bg and fg:
                return {"dark": _luma(bg) < 0.5, "accent": accent or BREEZE_ACCENT, "scheme": {"bg": bg, "view": view or bg, "fg": fg}}
            # no colors written: Plasma's default, Breeze (light)
            return {"dark": False, "accent": accent or BREEZE_ACCENT, "scheme": None}
    # anywhere else (GNOME too): the desktop portal tells light / dark and the accent color
    look = {"dark": True, "accent": BREEZE_ACCENT, "scheme": None}
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION)
        ask = lambda key: bus.call_sync("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
                                        "org.freedesktop.portal.Settings", "ReadOne", GLib.Variant("(ss)", ("org.freedesktop.appearance", key)),
                                        GLib.VariantType("(v)"), Gio.DBusCallFlags.NONE, 300, None).unpack()[0]
        look["dark"] = ask("color-scheme") != 2  # 1 = dark, 2 = light, 0 = no preference (Breeze dark then)
        accent = tuple(ask("accent-color"))
        if len(accent) == 3 and all(0 <= c <= 1 for c in accent):
            look["accent"] = accent
    except (GLib.Error, TypeError, ValueError):
        pass
    return look


def plasma_palette(mode="auto"):
    """bg, view, fg and accent colors of the Plasma theme. mode: auto (the desktop's look, light or dark), light, dark.
    The desktop is asked again at most once a second, so switching it to light or dark shows up on the dial by itself."""
    now = time.monotonic()
    try:
        mtime = os.stat(KDEGLOBALS).st_mtime
    except OSError:
        mtime = None
    if _system_look["look"] is None or now - _system_look["t"] > 1.0 and (mtime != _system_look["mtime"] or now - _system_look["t"] > 3.0):
        _system_look.update(t=now, mtime=mtime, look=_read_system_look())
    look = _system_look["look"]
    style = "dark" if look["dark"] else "light"
    if mode in ("light", "dark"):
        style = mode
    colors = look["scheme"] if look["scheme"] and look["dark"] == (style == "dark") else BREEZE[style]
    return {**colors, "accent": look["accent"], "dark": style == "dark"}


def theme_colors(theme):
    """(text, accent) colors of a theme: the user's, or the desktop's ones for the Plasma theme."""
    if theme.get("bg_type") == "plasma":
        pal = plasma_palette(theme.get("plasma_mode", "auto"))
        return pal["fg"], pal["accent"]
    return rgb(theme["text"], (1, 1, 1)), rgb(theme["accent"], (0.25, 0.55, 1.0))


# Breeze icons for the built-in modes and the messages (the emoji stays where the icon theme has none)
PLASMA_ICONS = {
    "↕": ("transform-move-vertical", "go-up"), "🔊": ("audio-volume-high",), "🔉": ("audio-volume-medium",),
    "🔈": ("audio-volume-low",), "🔇": ("audio-volume-muted",), "☀": ("brightness-high", "display-brightness"),
    "🔍": ("zoom-in",), "▶": ("media-playback-start",), "⏸": ("media-playback-pause",), "🗂": ("tab-duplicate", "tab-new"),
    "↔": ("object-flip-horizontal", "transform-move-horizontal"), "🏠": ("go-home", "user-home"), "⏻": ("system-shutdown",),
    "🎲": ("roll", "games-config-board"), "⏲": ("chronometer", "alarm-symbolic", "clock"), "⏩": ("media-seek-forward", "media-skip-forward"),
    "🌙": ("weather-clear-night", "redshift-status-on"), "🪟": ("window", "preferences-system-windows"),
    "🔎": ("edit-find",), "⌨": ("input-keyboard-brightness", "input-keyboard"), "🌐": ("globe", "preferences-desktop-locale"),
    "✨": ("games-highscores", "starred", "star-shape"), "🤖": ("dialog-messages", "im-user"),
    "🎮": ("preferences-desktop-display-randr", "video-display"), "😴": ("system-suspend",),
}
_icon_themes, _icons = {}, {}


def plasma_icon(cr, emoji, size, pal):
    """The Breeze (or the desktop's) icon for an emoji, as a cairo surface in the text color, or None."""
    names = PLASMA_ICONS.get(emoji)
    if not names:
        return None
    scale = max(1, round(cr.get_target().get_device_scale()[0]))
    key = (emoji, size, scale, pal["fg"], pal["dark"])
    if key not in _icons:
        style = "breeze-dark" if pal["dark"] else "breeze"
        if style not in _icon_themes:
            th = Gtk.IconTheme.new()
            if os.path.isdir(f"/usr/share/icons/{style}"):
                th.set_custom_theme(style)
            else:
                th = Gtk.IconTheme.get_default()
            _icon_themes[style] = th
        surf = None
        # the monochrome (-symbolic) variant first: GTK paints it in the theme's text color
        wanted = [v for n in names for v in (n + "-symbolic", n)]
        info = _icon_themes[style].choose_icon_for_scale(wanted, size, scale, Gtk.IconLookupFlags.FORCE_SIZE)
        if info is not None:
            try:
                fg = Gdk.RGBA(*pal["fg"], 1.0)
                pixbuf, _symbolic = info.load_symbolic(fg, None, None, None)
                surf = Gdk.cairo_surface_create_from_pixbuf(pixbuf, scale, None)
            except GLib.Error:
                surf = None
        _icons[key] = surf
    return _icons[key]


def _paint_icon(cr, surf, size, x, y):
    """Draw an icon surface centred on x, y."""
    cr.save()
    cr.set_source_surface(surf, round(x - size / 2), round(y - size / 2))
    cr.paint()
    cr.restore()


def blur_shape(kind, theme, msize, anim=None):
    """What the compositor should blur behind a menu / message window: ("circle", cx, cy, r) or ("rrect", x, y, w, h, r),
    following the appear/leave transition; None when the theme wants no blur."""
    if theme.get("blur", 0) <= 0 or kind not in ("menu", "osd"):
        return None
    if kind == "menu":
        pad = menu_pad(theme)
        W = msize + 2 * pad
        sc, _rot, dy = transition_geometry(*anim, W) if anim else (1.0, 0.0, 0.0)
        return ("circle", W / 2, W / 2 + dy, (msize / 2 - 5) * sc)
    pad = osd_pad(theme)
    W, Hh = OSD_W + 2 * pad, OSD_H + 2 * pad
    sc, _rot, dy = transition_geometry(*anim, Hh, osd=True) if anim else (1.0, 0.0, 0.0)
    cx, cy = W / 2, Hh * 0.7  # the point the message zooms around (see draw_osd)
    x, y = cx + (pad - cx) * sc, cy + (pad - cy) * sc + dy
    return ("rrect", x, y, OSD_W * sc, OSD_H * sc, 22 * sc)


def shape_rects(shape, scale):
    """The shape as rectangles (x, y, w, h) in device pixels, one per pixel row where it is curved."""
    out = []
    if shape[0] == "circle":
        _k, cx, cy, r = (shape[0], *(v * scale for v in shape[1:]))
        for y in range(int(cy - r), int(math.ceil(cy + r))):
            d = r * r - (y + 0.5 - cy) ** 2
            if d > 0:
                half = math.sqrt(d)
                out.append((int(round(cx - half)), y, max(1, int(round(2 * half))), 1))
        return out
    _k, x, y, w, h, r = (shape[0], *(v * scale for v in shape[1:]))
    x, y, w, h = int(round(x)), int(round(y)), int(round(w)), int(round(h))
    r = max(0, min(int(r), w // 2, h // 2))
    for i in range(r):  # the rounded rows, top and bottom
        inset = int(round(r - math.sqrt(max(0.0, r * r - (r - i - 0.5) ** 2))))
        out.append((x + inset, y + i, w - 2 * inset, 1))
        out.append((x + inset, y + h - 1 - i, w - 2 * inset, 1))
    out.append((x, y + r, w, h - 2 * r))
    return out


def _plasma_ring(cr, cx, cy, r_disc, r_in, pal, op):
    """Breeze-style disc: window color, the view color in the middle, hairline frames."""
    cr.set_source_rgba(*pal["bg"], op)
    cr.paint()
    g = cairo.LinearGradient(0, cy - r_disc, 0, cy + r_disc)  # the faint top-lit gradient of Plasma's surfaces
    g.add_color_stop_rgba(0, 1, 1, 1, 0.05 if pal["dark"] else 0.25)
    g.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.set_source(g)
    cr.paint()
    cr.new_path()
    cr.arc(cx, cy, r_in - 6, 0, 2 * math.pi)
    cr.set_source_rgba(*pal["view"], min(1.0, op + 0.1))
    cr.fill_preserve()
    cr.set_source_rgba(*pal["fg"], 0.12)
    cr.set_line_width(1)
    cr.stroke()


def _plasma_frame(cr, cx, cy, r_disc, pal):
    cr.new_path()
    cr.arc(cx, cy, r_disc - 0.5, 0, 2 * math.pi)
    cr.set_source_rgba(*pal["fg"], 0.2 if pal["dark"] else 0.25)
    cr.set_line_width(1)
    cr.stroke()


def _pill(cr, x, y, w, h):
    r = h / 2
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, math.pi / 2)
    cr.arc(x + r, y + r, r, math.pi / 2, 3 * math.pi / 2)
    cr.close_path()


def is_animated(theme):
    return theme.get("bg_type") in ("rainbow", "halloween", "christmas") or bool(theme.get("sparkles"))


def menu_pad(theme):
    return MENU_PAD_HALLOWEEN if theme.get("bg_type") in THEMED else MENU_PAD


def osd_pad(theme):
    return OSD_PAD_HALLOWEEN if theme.get("bg_type") in THEMED else OSD_PAD


# ------------------------------------------------------------------ animation helpers
def ease(name, u):
    """Motion curve. u in 0..1 -> about 0..1 (back/elastic overshoot a little)."""
    u = max(0.0, min(1.0, u))
    if name == "linear":
        return u
    if name == "back":
        c1 = 1.70158
        return 1 + (c1 + 1) * (u - 1) ** 3 + c1 * (u - 1) ** 2
    if name == "elastic":
        if u in (0.0, 1.0):
            return u
        return 2 ** (-10 * u) * math.sin((u * 10 - 0.75) * (2 * math.pi) / 3) + 1
    if name == "bounce":
        n1, d1 = 7.5625, 2.75
        if u < 1 / d1:
            return n1 * u * u
        if u < 2 / d1:
            u -= 1.5 / d1
            return n1 * u * u + 0.75
        if u < 2.5 / d1:
            u -= 2.25 / d1
            return n1 * u * u + 0.9375
        u -= 2.625 / d1
        return n1 * u * u + 0.984375
    return u * u * (3 - 2 * u)  # smooth


def sel_interp(frm, to, n, u, ease_name):
    """Position of the sliding highlight between slice frm and slice to (shortest way round the circle)."""
    d = ((to - frm + n / 2) % n) - n / 2
    return (frm + d * ease(ease_name, u)) % n


def transition_geometry(kind, p, ease_name, h, osd=False):
    """(scale, rotation, dy) of the picture at progress p of a transition (the fade and fan ones keep it in place)."""
    if kind == "none" or p >= 1.0:
        return 1.0, 0.0, 0.0
    p = max(0.0, p)
    e = ease(ease_name, p)
    if kind in ("zoom", "bounce", "spin"):
        sc = (0.55 + 0.45 * e) if kind == "zoom" else ((0.25 + 0.75 * ease("back", p)) if kind == "bounce" else 0.5 + 0.5 * e)
        return max(0.01, sc), (1 - e) * -math.pi / 2 if kind == "spin" else 0.0, 0.0
    if kind == "slide":
        return 1.0, 0.0, (1 - e) * h * (0.18 if osd else 0.08)
    return 1.0, 0.0, 0.0


def draw_transition(cr, kind, p, ease_name, w, h, cx, cy, draw, osd=False):
    """Draw draw(cr) while it appears (p going 0 -> 1) or goes away (p going 1 -> 0)."""
    if kind == "none" or p >= 1.0:
        draw(cr)
        return
    p = max(0.0, p)
    e = ease(ease_name, p)
    sc, rot, dy = transition_geometry(kind, p, ease_name, h, osd)
    alpha = max(0.0, min(1.0, e if kind in ("fade", "slide", "zoom", "spin") else p * 2.2))
    cr.save()
    cr.push_group()
    if kind == "fan":
        if osd:
            cr.rectangle(0, 0, w * min(1.0, e), h)
        else:
            cr.move_to(cx, cy)
            cr.arc(cx, cy, math.hypot(w, h), -math.pi / 2, -math.pi / 2 + 2 * math.pi * min(1.0, e) + 0.001)
            cr.close_path()
        cr.clip()
    elif kind in ("zoom", "bounce", "spin"):
        cr.translate(cx, cy)
        cr.rotate(rot)
        cr.scale(sc, sc)
        cr.translate(-cx, -cy)
    elif kind == "slide":
        cr.translate(0, dy)
    draw(cr)
    cr.pop_group_to_source()
    cr.paint_with_alpha(alpha)
    cr.restore()


def text(cr, s, size, x, y, center=True, bold=False):
    """Pango text (glyph fallback for emoji); y is the vertical centre."""
    layout = PangoCairo.create_layout(cr)
    layout.set_font_description(Pango.FontDescription(f"Sans {'Bold ' if bold else ''}{size}"))
    layout.set_text(s, -1)
    w, h = layout.get_pixel_size()
    cr.move_to(x - w / 2 if center else x, y - h / 2)
    PangoCairo.show_layout(cr, layout)


def text_segments(cr, segs, size, x, y, base, t):
    """Draw (string, colour) pieces one after another; colour None = base, "rainbow" = a moving rainbow."""
    layout = PangoCairo.create_layout(cr)
    layout.set_font_description(Pango.FontDescription(f"Sans Bold {size}"))
    for s, col in segs:
        for i, ch in enumerate(s if col == "rainbow" else [s]):
            layout.set_text(ch, -1)
            w, h = layout.get_pixel_size()
            if col == "rainbow":
                cr.set_source_rgba(*colorsys.hsv_to_rgb((t * 0.35 + i * 0.09) % 1.0, 0.75, 1.0), 1)
            else:
                cr.set_source_rgba(*(base if col is None else col), 1)
            cr.move_to(x, y - h / 2)
            PangoCairo.show_layout(cr, layout)
            x += w


def capture_backdrop(x, y, w, h, radius):
    """A blurred snapshot of the screen area x, y, w, h as a cairo surface (None if Pillow or the grab is unavailable)."""
    try:
        from PIL import ImageFilter, ImageGrab
        im = ImageGrab.grab(bbox=(x, y, x + w, y + h)).convert("RGBA").filter(ImageFilter.GaussianBlur(radius))
        data = bytearray(im.tobytes("raw", "BGRA"))
        return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, w, h, w * 4)
    except Exception:
        return None


_images = {}


def load_image(path):
    if not path:
        return None
    if path not in _images:
        try:
            _images[path] = cairo.ImageSurface.create_from_png(path)
        except Exception:
            _images[path] = None
    return _images[path]


def _star4(cr, x, y, sz):
    """A four-point sparkle."""
    k = sz * 0.1
    cr.move_to(x, y - sz)
    cr.curve_to(x + k, y - k, x + k, y - k, x + sz, y)
    cr.curve_to(x + k, y + k, x + k, y + k, x, y + sz)
    cr.curve_to(x - k, y + k, x - k, y + k, x - sz, y)
    cr.curve_to(x - k, y - k, x - k, y - k, x, y - sz)
    cr.close_path()


def _rounded(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def _sparkles(cr, cx, cy, radius, t, speed, color=(1, 1, 0.9), count=46, seed=7):
    rnd = random.Random(seed)
    for _ in range(count):
        ang, dist, ph, sz = rnd.uniform(0, 6.283), math.sqrt(rnd.random()) * 0.95, rnd.uniform(0, 6.283), rnd.uniform(0.012, 0.03)
        tw = 0.5 + 0.5 * math.sin(t * (2 + 3 * speed) + ph * 3)
        if tw < 0.15:
            continue
        _star4(cr, cx + math.cos(ang) * dist * radius, cy + math.sin(ang) * dist * radius, sz * radius * (0.5 + tw))
        cr.set_source_rgba(*color, 0.9 * tw)
        cr.fill()


# ------------------------------------------------------------------ backgrounds
def _bg_rainbow(cr, cx, cy, r, t, speed, opacity):
    n = 96
    for i in range(n):
        a0, a1 = i * 2 * math.pi / n, (i + 1.15) * 2 * math.pi / n
        cr.move_to(cx, cy)
        cr.arc(cx, cy, r, a0, a1)
        cr.close_path()
        h = (i / n + t * 0.12 * (0.3 + speed)) % 1.0
        cr.set_source_rgba(*colorsys.hsv_to_rgb(h, 0.75, 1.0), opacity)
        cr.fill()
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)  # soften the middle and keep the text readable
    g.add_color_stop_rgba(0, 0.05, 0.05, 0.1, 0.55)
    g.add_color_stop_rgba(0.6, 0.05, 0.05, 0.1, 0.3)
    g.add_color_stop_rgba(1, 0.05, 0.05, 0.1, 0.12)
    cr.set_source(g)
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.fill()


def _bg_image(cr, cx, cy, r, theme, opacity):
    img = load_image(theme.get("bg_image"))
    if img is None:
        cr.set_source_rgba(0.08, 0.08, 0.1, opacity)
        cr.paint()
        return
    cr.save()
    cr.translate(cx - r, cy - r)
    cr.scale(2 * r / img.get_width(), 2 * r / img.get_height())
    cr.set_source_surface(img, 0, 0)
    cr.paint_with_alpha(opacity)
    cr.restore()
    cr.set_source_rgba(0, 0, 0, theme.get("image_dim", 0.35))
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.fill()


# ------------------------------------------------------------------ Halloween artwork
def _ghost(cr, x, y, s, t, phase=0.0, alpha=0.9):
    """A friendly ghost; x, y = centre, s = width."""
    bob = math.sin(t * 2 + phase) * s * 0.08
    w, h = s, s * 1.2
    cr.save()
    cr.translate(x, y + bob)
    cr.rotate(math.sin(t * 1.3 + phase) * 0.08)
    cr.new_path()
    cr.move_to(-w / 2, h / 2)
    cr.line_to(-w / 2, -h * 0.05)
    cr.curve_to(-w / 2, -h * 0.65, w / 2, -h * 0.65, w / 2, -h * 0.05)
    cr.line_to(w / 2, h / 2)
    n = 4
    step = w / n
    for i in range(n):
        xa = w / 2 - step * i
        d = s * 0.16 * (1 + 0.35 * math.sin(t * 3 + i + phase))
        cr.curve_to(xa, h / 2 + d, xa - step, h / 2 + d, xa - step, h / 2)
    cr.close_path()
    g = cairo.LinearGradient(0, -h / 2, 0, h / 2)
    g.add_color_stop_rgba(0, 1, 1, 1, alpha)
    g.add_color_stop_rgba(1, 0.8, 0.85, 1, alpha * 0.8)
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgba(0.6, 0.65, 0.9, alpha * 0.6)
    cr.set_line_width(max(1.0, s * 0.02))
    cr.stroke()
    cr.set_source_rgba(0.08, 0.05, 0.15, alpha)
    for ex in (-0.2, 0.2):
        cr.save()
        cr.translate(ex * w, -h * 0.12)
        cr.scale(0.07 * w, 0.11 * w)
        cr.arc(0, 0, 1, 0, 2 * math.pi)
        cr.restore()
        cr.fill()
    cr.save()
    cr.translate(0, h * 0.1)
    cr.scale(0.07 * w, 0.09 * w * (1 + 0.3 * math.sin(t * 4 + phase)))
    cr.arc(0, 0, 1, 0, 2 * math.pi)
    cr.restore()
    cr.fill()
    cr.restore()


def _tombstone(cr, x, y, s, t, kind=0, eyes=False, phase=0.0):
    """x, y = bottom centre, s = width."""
    h = s * 1.3
    cr.save()
    cr.translate(x, y)
    cr.new_path()
    cr.move_to(-s / 2, 0)
    cr.line_to(-s / 2, -h + s / 2)
    cr.arc(0, -h + s / 2, s / 2, math.pi, 0)
    cr.line_to(s / 2, 0)
    cr.close_path()
    g = cairo.LinearGradient(-s / 2, -h, s / 2, 0)
    g.add_color_stop_rgb(0, 0.66, 0.68, 0.74)
    g.add_color_stop_rgb(1, 0.34, 0.36, 0.43)
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgb(0.14, 0.12, 0.2)
    cr.set_line_width(max(1.5, s * 0.05))
    cr.stroke()
    cr.set_source_rgb(0.16, 0.14, 0.22)
    if kind == 1:  # cross
        cr.set_line_width(max(2.0, s * 0.09))
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(0, -h * 0.82)
        cr.line_to(0, -h * 0.35)
        cr.move_to(-s * 0.2, -h * 0.65)
        cr.line_to(s * 0.2, -h * 0.65)
        cr.stroke()
    else:
        text(cr, "RIP", max(5, int(s * 0.22)), 0, -h * 0.55, bold=True)
    cr.set_source_rgba(0.25, 0.55, 0.25, 0.85)  # moss
    for mx, mr in ((-0.3, 0.1), (0.05, 0.07), (0.32, 0.09)):
        cr.arc(mx * s, -s * 0.03, mr * s, math.pi, 2 * math.pi)
        cr.fill()
    if eyes:  # glowing eyes peeking out
        fl = 0.6 + 0.4 * math.sin(t * 6 + phase)
        for ex in (-0.16, 0.16):
            gl = cairo.RadialGradient(ex * s, -h * 0.86, 0, ex * s, -h * 0.86, s * 0.18)
            gl.add_color_stop_rgba(0, 1, 0.2, 0.1, fl)
            gl.add_color_stop_rgba(1, 1, 0.2, 0.1, 0)
            cr.set_source(gl)
            cr.arc(ex * s, -h * 0.86, s * 0.18, 0, 2 * math.pi)
            cr.fill()
    cr.restore()


def _skeleton(cr, x, y, s, t, phase=0.0, bone=None):
    """A dancing skeleton; x, y = between the feet, s = height, bone = bone color."""
    sw = math.sin(t * 4 + phase)
    bone, dark = bone or (0.96, 0.95, 0.88), (0.1, 0.08, 0.16)
    cr.save()
    cr.translate(x + sw * s * 0.03, y)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)

    def limb(points, w):
        for color, width in ((dark, w * 1.7), (bone, w)):
            cr.set_source_rgb(*color)
            cr.set_line_width(width)
            cr.move_to(*points[0])
            for p in points[1:]:
                cr.line_to(*p)
            cr.stroke()

    lw = s * 0.035
    hip = (0, -s * 0.38)
    for side in (-1, 1):  # legs: one kicks
        k = math.sin(t * 4 + phase + (0 if side < 0 else math.pi)) * 0.35
        knee = (side * s * 0.06 + k * s * 0.1, -s * 0.2)
        foot = (side * s * 0.09 + k * s * 0.2, 0)
        limb([hip, knee, foot], lw)
    limb([(0, -s * 0.72), hip], lw * 1.1)  # spine
    for i, wd in enumerate((0.2, 0.18, 0.14)):  # ribs
        yy = -s * (0.66 - 0.06 * i)
        limb([(-s * wd / 2, yy), (s * wd / 2, yy)], lw * 0.7)
    shoulder_y = -s * 0.68
    limb([(-s * 0.1, shoulder_y), (-s * 0.17, -s * 0.55 + sw * s * 0.03), (-s * 0.14, -s * 0.44 + sw * s * 0.05)], lw)
    wave = math.sin(t * 6 + phase)  # right arm waves above the head
    limb([(s * 0.1, shoulder_y), (s * 0.2, -s * 0.78), (s * 0.18 + wave * s * 0.05, -s * 0.95)], lw)
    limb([(-s * 0.1, -s * 0.38), (s * 0.1, -s * 0.38)], lw * 1.2)  # pelvis
    head = (0, -s * 0.82)
    cr.arc(*head, s * 0.115, 0, 2 * math.pi)  # skull
    cr.set_source_rgb(*bone)
    cr.fill_preserve()
    cr.set_source_rgb(*dark)
    cr.set_line_width(lw * 0.8)
    cr.stroke()
    cr.set_source_rgb(*dark)
    for ex in (-0.045, 0.045):
        cr.arc(head[0] + ex * s, head[1] - s * 0.01, s * 0.03, 0, 2 * math.pi)
        cr.fill()
    cr.move_to(head[0], head[1] + s * 0.02)  # nose
    cr.line_to(head[0] - s * 0.012, head[1] + s * 0.05)
    cr.line_to(head[0] + s * 0.012, head[1] + s * 0.05)
    cr.fill()
    cr.set_line_width(lw * 0.45)  # teeth
    for tx in (-0.04, -0.013, 0.013, 0.04):
        cr.move_to(head[0] + tx * s, head[1] + s * 0.07)
        cr.line_to(head[0] + tx * s, head[1] + s * 0.098)
    cr.stroke()
    cr.restore()


def _pumpkin(cr, x, y, s, t, phase=0.0):
    """A jack-o'-lantern; x, y = bottom centre, s = width."""
    h = s * 0.82
    cr.save()
    cr.translate(x, y - h / 2)
    fl = 0.8 + 0.2 * math.sin(t * 9 + phase)
    gl = cairo.RadialGradient(0, 0, 0, 0, 0, s * 0.9)
    gl.add_color_stop_rgba(0, 1, 0.6, 0.1, 0.35 * fl)
    gl.add_color_stop_rgba(1, 1, 0.5, 0.0, 0)
    cr.set_source(gl)
    cr.arc(0, 0, s * 0.9, 0, 2 * math.pi)
    cr.fill()
    for dx, wd in ((-0.28, 0.5), (0.28, 0.5), (0, 0.55)):  # lobes
        cr.save()
        cr.translate(dx * s, 0)
        cr.scale(wd * s / 2, h / 2)
        cr.arc(0, 0, 1, 0, 2 * math.pi)
        cr.restore()
        g = cairo.LinearGradient(0, -h / 2, 0, h / 2)
        g.add_color_stop_rgb(0, 1.0, 0.62, 0.12)
        g.add_color_stop_rgb(1, 0.85, 0.35, 0.04)
        cr.set_source(g)
        cr.fill_preserve()
        cr.set_source_rgb(0.45, 0.18, 0.02)
        cr.set_line_width(max(1.0, s * 0.025))
        cr.stroke()
    cr.set_source_rgb(0.25, 0.4, 0.12)  # stem
    cr.rectangle(-s * 0.05, -h / 2 - s * 0.14, s * 0.1, s * 0.16)
    cr.fill()
    cr.set_source_rgba(1, 0.9, 0.3, fl)  # glowing face
    for ex in (-0.2, 0.2):
        cr.move_to(ex * s, -h * 0.28)
        cr.line_to(ex * s - s * 0.09, -h * 0.02)
        cr.line_to(ex * s + s * 0.09, -h * 0.02)
        cr.close_path()
        cr.fill()
    cr.move_to(0, h * 0.02)
    cr.line_to(-s * 0.05, h * 0.12)
    cr.line_to(s * 0.05, h * 0.12)
    cr.close_path()
    cr.fill()
    cr.move_to(-s * 0.3, h * 0.2)
    for i, px in enumerate((-0.2, -0.1, 0.0, 0.1, 0.2, 0.3)):
        cr.line_to(px * s, h * (0.3 if i % 2 == 0 else 0.2))
    cr.line_to(s * 0.3, h * 0.2)
    cr.line_to(s * 0.3, h * 0.28)
    cr.line_to(-s * 0.3, h * 0.28)
    cr.close_path()
    cr.fill()
    cr.restore()


def _bat(cr, x, y, s, t, phase=0.0):
    f = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 13 + phase))  # wing flap
    cr.save()
    cr.translate(x, y)
    cr.set_source_rgb(0.05, 0.02, 0.09)
    for side in (-1, 1):
        cr.move_to(0, -s * 0.05)
        cr.curve_to(side * s * 0.3, -s * 0.55 * f, side * s * 0.7, -s * 0.45 * f, side * s, -s * 0.2 * f)
        cr.curve_to(side * s * 0.88, s * 0.08, side * s * 0.75, s * 0.02, side * s * 0.65, s * 0.18)
        cr.curve_to(side * s * 0.52, s * 0.04, side * s * 0.38, s * 0.12, side * s * 0.25, s * 0.2)
        cr.line_to(0, s * 0.12)
        cr.close_path()
        cr.fill()
    cr.save()
    cr.scale(s * 0.13, s * 0.2)
    cr.arc(0, 0, 1, 0, 2 * math.pi)
    cr.restore()
    cr.fill()
    for side in (-1, 1):
        cr.move_to(side * s * 0.06, -s * 0.14)
        cr.line_to(side * s * 0.1, -s * 0.3)
        cr.line_to(side * s * 0.14, -s * 0.12)
        cr.fill()
        cr.arc(side * s * 0.055, -s * 0.06, s * 0.025, 0, 2 * math.pi)
        cr.set_source_rgb(1, 0.2, 0.1)
        cr.fill()
        cr.set_source_rgb(0.05, 0.02, 0.09)
    cr.restore()


def _spider(cr, x, y0, length, t):
    ln = length * (0.85 + 0.15 * math.sin(t * 1.4))
    cr.set_source_rgba(1, 1, 1, 0.55)
    cr.set_line_width(1.2)
    cr.move_to(x, y0)
    cr.line_to(x, y0 + ln)
    cr.stroke()
    cr.save()
    cr.translate(x, y0 + ln + 9)
    cr.set_source_rgb(0.07, 0.04, 0.1)
    cr.set_line_width(1.8)
    for i in range(4):
        for side in (-1, 1):
            a = (i - 1.5) * 0.45
            kx, ky = side * 13, a * 12 - 4
            cr.move_to(side * 4, a * 3)
            cr.line_to(kx, ky)
            cr.line_to(side * 17, ky + 9)
    cr.stroke()
    cr.arc(0, 2, 8, 0, 2 * math.pi)
    cr.fill()
    cr.arc(0, -6, 5, 0, 2 * math.pi)
    cr.fill()
    cr.set_source_rgb(1, 0.15, 0.1)
    for ex in (-2, 2):
        cr.arc(ex, -7, 1.3, 0, 2 * math.pi)
        cr.fill()
    cr.restore()


def _cobweb(cr, x, y, size, flip_x=1, flip_y=1):
    cr.save()
    cr.translate(x, y)
    cr.scale(flip_x, flip_y)
    cr.set_source_rgba(1, 1, 1, 0.55)
    cr.set_line_width(1.1)
    angs = [i * math.pi / 8 for i in range(5)]
    for a in angs:
        cr.move_to(0, 0)
        cr.line_to(size * math.cos(a), size * math.sin(a))
    cr.stroke()
    for frac in (0.3, 0.52, 0.76, 1.0):
        r = size * frac
        cr.move_to(r * math.cos(angs[0]), r * math.sin(angs[0]))
        for a0, a1 in zip(angs, angs[1:]):
            am = (a0 + a1) / 2
            cr.curve_to(r * 0.8 * math.cos(am), r * 0.8 * math.sin(am), r * 0.8 * math.cos(am), r * 0.8 * math.sin(am),
                        r * math.cos(a1), r * math.sin(a1))
        cr.stroke()
    cr.restore()


def _moon(cr, x, y, r, alpha=1.0):
    gl = cairo.RadialGradient(x, y, r * 0.8, x, y, r * 2)
    gl.add_color_stop_rgba(0, 1, 0.95, 0.7, 0.35 * alpha)
    gl.add_color_stop_rgba(1, 1, 0.95, 0.7, 0)
    cr.set_source(gl)
    cr.arc(x, y, r * 2, 0, 2 * math.pi)
    cr.fill()
    g = cairo.RadialGradient(x - r * 0.3, y - r * 0.3, 0, x, y, r)
    g.add_color_stop_rgba(0, 1, 1, 0.88, alpha)
    g.add_color_stop_rgba(1, 0.95, 0.88, 0.6, alpha)
    cr.set_source(g)
    cr.arc(x, y, r, 0, 2 * math.pi)
    cr.fill()
    cr.set_source_rgba(0.8, 0.72, 0.45, 0.45 * alpha)
    for dx, dy, rr in ((-0.3, -0.2, 0.18), (0.25, 0.1, 0.22), (-0.1, 0.4, 0.12)):
        cr.arc(x + dx * r, y + dy * r, rr * r, 0, 2 * math.pi)
        cr.fill()


def _halloween_disc(cr, cx, cy, r, t, speed, opacity):
    """Inside the menu disc: night sky, moon, stars, drifting mist, bats and ghosts."""
    g = cairo.RadialGradient(cx, cy - r * 0.2, 0, cx, cy, r)
    g.add_color_stop_rgba(0, 0.28, 0.1, 0.38, opacity)
    g.add_color_stop_rgba(0.7, 0.12, 0.04, 0.2, opacity)
    g.add_color_stop_rgba(1, 0.04, 0.01, 0.08, opacity)
    cr.set_source(g)
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.fill()
    _sparkles(cr, cx, cy, r, t, speed, color=(1, 0.9, 0.6), count=30, seed=11)
    for k in range(3):  # mist
        mx = cx + ((t * 14 * (0.5 + speed) + k * r * 0.9) % (2.6 * r)) - 1.3 * r
        my = cy + r * (0.55 + 0.12 * k)
        mg = cairo.RadialGradient(mx, my, 0, mx, my, r * 0.55)
        mg.add_color_stop_rgba(0, 0.8, 0.75, 1, 0.16)
        mg.add_color_stop_rgba(1, 0.8, 0.75, 1, 0)
        cr.set_source(mg)
        cr.save()
        cr.translate(mx, my)
        cr.scale(1, 0.35)
        cr.translate(-mx, -my)
        cr.arc(mx, my, r * 0.55, 0, 2 * math.pi)
        cr.restore()
        cr.fill()
    for k in range(2):  # bats crossing the disc
        u = ((t * 0.16 * (0.5 + speed) + k * 0.5) % 1.0)
        _bat(cr, cx - r * 1.1 + u * r * 2.2, cy - r * (0.55 - 0.25 * k) + math.sin(u * 14) * r * 0.05, r * 0.11, t, phase=k * 2)
    for k in range(2):  # translucent ghosts drifting behind the slices
        u = ((t * 0.05 * (0.5 + speed) + k * 0.5) % 1.0)
        _ghost(cr, cx + (-0.8 + 1.6 * (u if k == 0 else 1 - u)) * r, cy + r * (0.15 - 0.35 * k), r * 0.15, t, phase=k * 3, alpha=0.18)


def _halloween_frame(cr, pad, size_w, size_h, cx_disc, cy_disc, r_disc, t, speed):
    """Around the menu: graveyard with skeleton and pumpkins at the bottom, cobwebs, spider, moon-lit ghosts and bats."""
    w, h = size_w, size_h
    # ground
    cr.save()
    cr.rectangle(0, h - pad * 0.38, w, pad * 0.38)
    cr.clip()
    g = cairo.LinearGradient(0, h - pad * 0.4, 0, h)
    g.add_color_stop_rgb(0, 0.13, 0.06, 0.2)
    g.add_color_stop_rgb(1, 0.05, 0.02, 0.08)
    cr.set_source(g)
    cr.paint()
    cr.restore()
    base = h - pad * 0.1
    # bottom corners: skeleton (left), pumpkins (right), tombstones between
    _skeleton(cr, pad * 0.9, base, pad * 1.45, t, 0)
    _tombstone(cr, pad * 1.95, base, pad * 0.5, t, 0, True, 0)
    _tombstone(cr, w - pad * 2.1, base, pad * 0.46, t, 1, True, 2)
    _tombstone(cr, w * 0.5 - pad * 0.3, base + 2, pad * 0.4, t, 0, False)
    _tombstone(cr, w * 0.5 + pad * 0.5, base + 2, pad * 0.36, t, 1, False)
    _pumpkin(cr, w - pad * 1.0, base + 4, pad * 0.95, t, 1)
    _pumpkin(cr, w - pad * 1.75, base + 6, pad * 0.5, t, 2)
    # top corners
    _cobweb(cr, 0, 0, pad * 1.5)
    _cobweb(cr, w, 0, pad * 1.5, flip_x=-1)
    _spider(cr, pad * 1.55, 0, pad * 0.95, t)
    _moon(cr, w - pad * 0.95, pad * 0.95, pad * 0.3, 0.95)
    # sides: ghosts
    _ghost(cr, pad * 0.5, h * 0.4, pad * 0.62, t, 0.5, 0.88)
    _ghost(cr, w - pad * 0.48, h * 0.62, pad * 0.55, t, 2.2, 0.85)
    # bats flying around
    for k in range(3):
        u = (t * 0.1 * (0.5 + speed) + k / 3) % 1.0
        _bat(cr, -pad * 0.3 + u * (w + pad * 0.6), pad * (0.35 + 0.5 * k) + math.sin(u * 20 + k) * pad * 0.18, pad * 0.34, t, phase=k * 1.7)


def _halloween_osd_frame(cr, pad, w, h, t, speed):
    """Around the little message box: pumpkin, ghost, bat, spider, tiny graveyard."""
    bx, by, bw, bh = pad, pad, w - 2 * pad, h - 2 * pad
    _pumpkin(cr, bx + pad * 0.8, by + 6, pad * 0.9, t, 0)
    _ghost(cr, bx + bw - pad * 0.6, by - pad * 0.1, pad * 0.75, t, 1.5, 0.9)
    _spider(cr, bx + bw * 0.5, 0, by - 2, t)
    u = (t * 0.2 * (0.5 + speed)) % 1.0
    _bat(cr, u * w, pad * 0.35 + math.sin(u * 16) * pad * 0.12, pad * 0.4, t)
    base = by + bh + pad * 0.78
    for i, kx in enumerate((0.12, 0.3, 0.62, 0.84)):
        _tombstone(cr, bx + bw * kx, base, pad * 0.38, t, i % 2, i == 0, i)
    _skeleton(cr, bx + bw * 0.48, base + 2, pad * 0.9, t, 1)


# ------------------------------------------------------------------ the menu
def draw_menu(cr, theme, items, sel, t, msize, backdrop=None, sel_pos=None, anim=None):
    """items: [(icon, name)]. cr origin = top-left of the window (size msize + 2 * pad).
    sel_pos = where the highlight is (float, while it slides); anim = (kind, p, ease_name) while appearing or leaving."""
    pad = menu_pad(theme)
    W = msize + 2 * pad
    draw = lambda c: _menu_body(c, theme, items, sel, t, msize, backdrop, sel if sel_pos is None else sel_pos)
    if anim is None:
        draw(cr)
    else:
        draw_transition(cr, anim[0], anim[1], anim[2], W, W, W / 2, W / 2, draw)


def _menu_body(cr, theme, items, sel, t, msize, backdrop, sp):
    pad = menu_pad(theme)
    R = msize / 2
    cx = cy = pad + R
    Wd = msize + 2 * pad
    framed = theme["bg_type"] in THEMED
    tc, accent = theme_colors(theme)
    plasma = theme["bg_type"] == "plasma"
    pal = plasma_palette(theme.get("plasma_mode", "auto")) if plasma else None
    r_disc, r_out, r_in = R - 5, R - 10, 105
    r_txt = r_in + 0.53 * (r_out - r_in)
    n = max(1, len(items))

    if theme["shadow"]:  # soft shadow under the disc
        s = theme["shadow_strength"]
        g = cairo.RadialGradient(cx, cy + 8, r_disc * 0.88, cx, cy + 8, r_disc + pad * 0.85)
        g.add_color_stop_rgba(0, 0, 0, 0, 0.6 * s)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        cr.set_source(g)
        cr.arc(cx, cy + 8, r_disc + pad * 0.85, 0, 2 * math.pi)
        cr.fill()
    if theme["glow"]:  # glowing rim
        gc = rgb(theme["glow_color"], accent)
        g = cairo.RadialGradient(cx, cy, r_disc * 0.96, cx, cy, r_disc + pad * 0.7)
        g.add_color_stop_rgba(0, *gc, 0.7 * theme["glow_strength"])
        g.add_color_stop_rgba(1, *gc, 0)
        cr.set_source(g)
        cr.arc(cx, cy, r_disc + pad * 0.7, 0, 2 * math.pi)
        cr.fill()

    cr.save()  # ---- disc content
    cr.arc(cx, cy, r_disc, 0, 2 * math.pi)
    cr.clip()
    if backdrop is not None:
        cr.set_source_surface(backdrop, 0, 0)
        cr.paint()
    op = theme["bg_opacity"]
    kind = theme["bg_type"]
    if kind == "rainbow":
        _bg_rainbow(cr, cx, cy, r_disc, t, theme["speed"], op)
    elif kind == "image":
        _bg_image(cr, cx, cy, r_disc, theme, op)
    elif kind == "halloween":
        _halloween_disc(cr, cx, cy, r_disc, t, theme["speed"], op)
    elif kind == "christmas":
        _xmas_disc(cr, cx, cy, r_disc, t, theme["speed"], op)
    elif plasma:
        _plasma_ring(cr, cx, cy, r_disc, r_in, pal, op)
    else:
        cr.set_source_rgba(*rgb(theme["bg_color"], (0.08, 0.08, 0.1)), op)
        cr.paint()
    step = 2 * math.pi / n
    for i in range(n):  # slices
        a0 = -math.pi / 2 + (i - 0.5) * step
        if plasma:  # Plasma keeps it airy: hairline separators instead of filled slices
            cr.new_path()
            cr.move_to(cx + (r_in + 4) * math.cos(a0), cy + (r_in + 4) * math.sin(a0))
            cr.line_to(cx + (r_out - 4) * math.cos(a0), cy + (r_out - 4) * math.sin(a0))
            cr.set_source_rgba(*tc, 0.08)
            cr.set_line_width(1)
            cr.stroke()
            continue
        cr.new_path()
        cr.arc(cx, cy, r_out, a0 + 0.02, a0 + step - 0.02)
        cr.arc_negative(cx, cy, r_in, a0 + step - 0.02, a0 + 0.02)
        cr.close_path()
        cr.set_source_rgba(*tc, 0.04 if plasma else 0.07 if kind not in THEMED else 0.05)
        cr.fill()
    a0 = -math.pi / 2 + (sp - 0.5) * step  # the highlighted slice (it can sit between two slices while it slides)
    cr.new_path()
    cr.arc(cx, cy, r_out, a0 + 0.02, a0 + step - 0.02)
    cr.arc_negative(cx, cy, r_in, a0 + step - 0.02, a0 + 0.02)
    cr.close_path()
    if theme["glow"]:
        gc = rgb(theme["glow_color"], accent)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        for lw, al in ((26, 0.08), (16, 0.14), (8, 0.22)):
            cr.set_source_rgba(*gc, al * (0.4 + theme["glow_strength"]))
            cr.set_line_width(lw)
            cr.stroke_preserve()
    if plasma:  # Breeze's selection: a tinted fill with a solid accent frame, plus an indicator line on the rim
        cr.set_source_rgba(*accent, 0.3 if pal["dark"] else 0.22)
        cr.fill_preserve()
        cr.set_source_rgba(*accent, 1)
        cr.set_line_width(1.5)
        cr.stroke()
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_width(4)
        cr.new_path()
        cr.arc(cx, cy, r_disc - 4, a0 + step * 0.22, a0 + step * 0.78)
        cr.stroke()
        cr.set_line_cap(cairo.LINE_CAP_BUTT)
    else:
        cr.set_source_rgba(*accent, 0.95)
        cr.fill()
    if theme["reflection"] > 0:  # glossy highlight on the upper part
        k = theme["reflection"]
        cr.save()
        cr.save()
        cr.translate(cx, cy - r_disc * 0.42)
        cr.scale(r_disc * 0.92, r_disc * 0.55)
        cr.arc(0, 0, 1, 0, 2 * math.pi)
        cr.restore()
        g = cairo.LinearGradient(0, cy - r_disc, 0, cy)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.42 * k)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        cr.set_source(g)
        cr.fill()
        cr.restore()
        cr.set_line_width(2)
        cr.arc(cx, cy, r_disc - 2, math.pi * 1.1, math.pi * 1.9)
        cr.set_source_rgba(1, 1, 1, 0.35 * k)
        cr.stroke()
    if theme["sparkles"] and kind not in THEMED:
        _sparkles(cr, cx, cy, r_disc, t, theme["speed"], seed=3)
    if kind == "rainbow":
        _sparkles(cr, cx, cy, r_disc, t, theme["speed"], seed=5, count=34)
    for i, (icon, name) in enumerate(items):  # icons and names
        am = -math.pi / 2 + i * 2 * math.pi / n
        tx, ty = cx + r_txt * math.cos(am), cy + r_txt * math.sin(am)
        cr.set_source_rgba(*tc, 1)
        surf = plasma_icon(cr, icon, 24, pal) if plasma else None
        if surf:
            _paint_icon(cr, surf, 24, tx, ty - 10)
        else:
            text(cr, icon, 20, tx, ty - 11)
        text(cr, name, 9, tx, ty + 17)
    if items:
        icon, name = items[min(sel, len(items) - 1)]
        surf = plasma_icon(cr, icon, 48, pal) if plasma else None
        cr.set_source_rgba(*tc, 0.92)
        if surf:  # Plasma: the chosen mode big in the middle, like its OSDs
            _paint_icon(cr, surf, 48, cx, cy - 14)
            text(cr, name, 12, cx, cy + 32)
        else:
            text(cr, name, 13, cx, cy)
    if plasma:
        _plasma_frame(cr, cx, cy, r_disc, pal)
    cr.restore()

    if framed:
        (_xmas_frame if kind == "christmas" else _halloween_frame)(cr, pad, Wd, Wd, cx, cy, r_disc, t, theme["speed"])


# ------------------------------------------------------------------ the on-screen message
def draw_osd(cr, theme, label, value, t, backdrop=None, anim=None):
    """cr origin = top-left of the window (size OSD_W + 2 pad, OSD_H + 2 pad)."""
    pad = osd_pad(theme)
    W, Hh = OSD_W + 2 * pad, OSD_H + 2 * pad
    draw = lambda c: _osd_body(c, theme, label, value, t, backdrop)
    if anim is None:
        draw(cr)
    else:
        draw_transition(cr, anim[0], anim[1], anim[2], W, Hh, W / 2, Hh * 0.7, draw, osd=True)


def _osd_body(cr, theme, label, value, t, backdrop):
    pad = osd_pad(theme)
    w, h, r = OSD_W, OSD_H, 22
    x0, y0 = pad, pad
    tc, accent = theme_colors(theme)
    kind = theme["bg_type"]
    pal = plasma_palette(theme.get("plasma_mode", "auto")) if kind == "plasma" else None

    def box():
        cr.new_sub_path()
        cr.arc(x0 + w - r, y0 + r, r, -math.pi / 2, 0)
        cr.arc(x0 + w - r, y0 + h - r, r, 0, math.pi / 2)
        cr.arc(x0 + r, y0 + h - r, r, math.pi / 2, math.pi)
        cr.arc(x0 + r, y0 + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    if theme["shadow"]:
        s = theme["shadow_strength"]
        for grow, al in ((14, 0.05), (9, 0.08), (5, 0.12), (2, 0.16)):
            _rounded(cr, x0 - grow, y0 - grow + 5, w + 2 * grow, h + 2 * grow, r + grow)
            cr.set_source_rgba(0, 0, 0, al * s * 1.6)
            cr.fill()
    if theme["glow"]:
        gc = rgb(theme["glow_color"], accent)
        for grow, al in ((14, 0.05), (9, 0.09), (5, 0.14), (2, 0.2)):
            _rounded(cr, x0 - grow, y0 - grow, w + 2 * grow, h + 2 * grow, r + grow)
            cr.set_source_rgba(*gc, al * theme["glow_strength"] * 1.4)
            cr.fill()
    cr.save()
    box()
    cr.clip()
    if backdrop is not None:
        cr.set_source_surface(backdrop, 0, 0)
        cr.paint()
    op = theme["bg_opacity"]
    if kind == "rainbow":
        _bg_rainbow(cr, x0 + w / 2, y0 + h / 2, w * 0.62, t, theme["speed"], op)
        cr.set_source_rgba(0.05, 0.05, 0.1, 0.35)
        cr.paint()
    elif kind == "image":
        _bg_image(cr, x0 + w / 2, y0 + h / 2, w / 2, theme, op)
    elif kind == "halloween":
        g = cairo.LinearGradient(x0, y0, x0 + w, y0 + h)
        g.add_color_stop_rgba(0, 0.22, 0.08, 0.32, op)
        g.add_color_stop_rgba(1, 0.06, 0.02, 0.1, op)
        cr.set_source(g)
        cr.paint()
        _sparkles(cr, x0 + w / 2, y0 + h / 2, w * 0.45, t, theme["speed"], color=(1, 0.9, 0.6), count=14, seed=2)
    elif kind == "christmas":
        g = cairo.LinearGradient(x0, y0, x0 + w, y0 + h)
        g.add_color_stop_rgba(0, 0.08, 0.3, 0.21, op)
        g.add_color_stop_rgba(1, 0.02, 0.1, 0.1, op)
        cr.set_source(g)
        cr.paint()
        _sparkles(cr, x0 + w / 2, y0 + h / 2, w * 0.45, t, theme["speed"], color=XMAS_GOLD, count=14, seed=2)
        _snowfall(cr, x0, y0, w, h, t, theme["speed"], count=16, seed=3, size=0.9)
    elif pal:
        cr.set_source_rgba(*pal["bg"], op)
        cr.paint()
        g = cairo.LinearGradient(0, y0, 0, y0 + h)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.05 if pal["dark"] else 0.25)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        cr.set_source(g)
        cr.paint()
    else:
        cr.set_source_rgba(*rgb(theme["bg_color"], (0.08, 0.08, 0.1)), op)
        cr.paint()
    if theme["reflection"] > 0:
        k = theme["reflection"]
        g = cairo.LinearGradient(0, y0, 0, y0 + h * 0.55)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.35 * k)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        cr.set_source(g)
        cr.rectangle(x0, y0, w, h * 0.55)
        cr.fill()
    if theme["sparkles"] and kind not in THEMED:
        _sparkles(cr, x0 + w / 2, y0 + h / 2, w * 0.5, t, theme["speed"], seed=4, count=20)
    cr.restore()

    cr.set_source_rgba(*tc, 1)
    has_bar = value is not None
    icon_surf, tx = None, x0 + 24
    if pal and isinstance(label, str):  # Plasma's OSD: the icon on the left, then the text and the bar
        first, _sp, rest = label.partition(" ")
        icon_surf = plasma_icon(cr, first, 40, pal) if rest else None
        if icon_surf:
            _paint_icon(cr, icon_surf, 40, x0 + 46, y0 + h / 2)
            label, tx = rest, x0 + 82
    if isinstance(label, list):
        text_segments(cr, label, 15, x0 + 24, y0 + (34 if has_bar else h / 2), tc, t)
    else:
        text(cr, label, 15, tx, y0 + (34 if has_bar else h / 2), center=False)
    if has_bar and pal:  # Plasma's OSD: a thin rounded trough with the accent inside
        v = max(0.0, min(1.0, value))
        bw = x0 + w - 24 - tx
        _pill(cr, tx, y0 + 68, bw, 8)
        cr.set_source_rgba(*tc, 0.15)
        cr.fill()
        if v > 0:
            _pill(cr, tx, y0 + 68, max(8.0, bw * v), 8)
            cr.set_source_rgba(*accent, 1)
            cr.fill()
    elif has_bar:
        cr.set_source_rgba(*tc, 0.2)
        cr.rectangle(x0 + 24, y0 + 66, w - 48, 12)
        cr.fill()
        cr.set_source_rgba(*accent, 1)
        cr.rectangle(x0 + 24, y0 + 66, (w - 48) * max(0.0, min(1.0, value)), 12)
        cr.fill()
    if pal:
        box()
        cr.set_source_rgba(*pal["fg"], 0.2 if pal["dark"] else 0.25)
        cr.set_line_width(1)
        cr.stroke()
    if kind == "halloween":
        _halloween_osd_frame(cr, pad, w + 2 * pad, h + 2 * pad, t, theme["speed"])
    elif kind == "christmas":
        _xmas_osd_frame(cr, pad, w + 2 * pad, h + 2 * pad, t, theme["speed"])


def house_picture(w=640, h=480):
    """A little illustrated house drawn with cairo: the picture of the House mode when you have not put your own."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(surf)
    cr.scale(w / 640, h / 480)

    def rgb(r, g, b, a=1.0):
        cr.set_source_rgba(r, g, b, a)

    def disc(x, y, r):
        cr.arc(x, y, r, 0, 2 * math.pi)
        cr.fill()

    sky = cairo.LinearGradient(0, 0, 0, 330)  # sky
    sky.add_color_stop_rgb(0, 0.33, 0.58, 0.92)
    sky.add_color_stop_rgb(1, 0.84, 0.93, 1.0)
    cr.set_source(sky)
    cr.paint()
    glow = cairo.RadialGradient(530, 85, 8, 530, 85, 95)  # sun
    glow.add_color_stop_rgba(0, 1, 0.95, 0.6, 1)
    glow.add_color_stop_rgba(1, 1, 0.95, 0.6, 0)
    cr.set_source(glow)
    disc(530, 85, 95)
    rgb(1, 0.91, 0.45)
    disc(530, 85, 34)
    rgb(1, 1, 1, 0.9)  # clouds
    for x, y, s in ((110, 90, 1.0), (300, 60, 0.8)):
        for dx, dy, r in ((0, 0, 24), (26, -10, 30), (56, 2, 22), (28, 8, 24)):
            disc(x + dx * s, y + dy * s, r * s)
    rgb(0.55, 0.76, 0.43)  # far hills
    cr.move_to(0, 340)
    cr.curve_to(140, 270, 300, 290, 420, 322)
    cr.curve_to(520, 346, 590, 300, 640, 312)
    cr.line_to(640, 480)
    cr.line_to(0, 480)
    cr.fill()
    rgb(0.40, 0.67, 0.32)  # lawn
    cr.move_to(0, 372)
    cr.curve_to(200, 350, 440, 352, 640, 374)
    cr.line_to(640, 480)
    cr.line_to(0, 480)
    cr.fill()
    rgb(0.89, 0.81, 0.63)  # path
    cr.move_to(300, 392)
    cr.line_to(344, 392)
    cr.line_to(420, 480)
    cr.line_to(230, 480)
    cr.fill()
    rgb(0.33, 0.20, 0.12)  # trunk and leaves
    cr.rectangle(545, 312, 16, 74)
    cr.fill()
    for x, y, r, c in ((553, 286, 46, (0.22, 0.52, 0.27)), (524, 312, 33, (0.27, 0.58, 0.30)), (584, 314, 31, (0.25, 0.55, 0.28))):
        rgb(*c)
        disc(x, y, r)
    rgb(0, 0, 0, 0.12)  # house shadow
    cr.save()
    cr.translate(332, 396)
    cr.scale(1, 0.12)
    disc(0, 0, 175)
    cr.restore()
    rgb(0.62, 0.21, 0.17)  # chimney
    cr.rectangle(398, 134, 32, 70)
    cr.fill()
    rgb(0.45, 0.14, 0.12)
    cr.rectangle(392, 128, 44, 12)
    cr.fill()
    rgb(0.75, 0.75, 0.78, 0.65)  # smoke
    for x, y, r in ((414, 108, 11), (426, 88, 14), (444, 66, 17)):
        disc(x, y, r)
    rgb(0.99, 0.93, 0.80)  # walls
    cr.rectangle(180, 232, 280, 160)
    cr.fill()
    rgb(0.93, 0.85, 0.70)
    cr.rectangle(180, 366, 280, 26)
    cr.fill()
    rgb(0.74, 0.25, 0.20)  # roof
    cr.move_to(146, 240)
    cr.line_to(320, 112)
    cr.line_to(494, 240)
    cr.close_path()
    cr.fill()
    rgb(0.55, 0.16, 0.13)
    cr.set_line_width(8)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.move_to(146, 240)
    cr.line_to(320, 112)
    cr.line_to(494, 240)
    cr.stroke()
    rgb(1, 1, 1)  # round attic window
    disc(320, 188, 21)
    rgb(1, 0.88, 0.5)
    disc(320, 188, 16)
    rgb(1, 1, 1)
    cr.set_line_width(3)
    cr.move_to(304, 188)
    cr.line_to(336, 188)
    cr.move_to(320, 172)
    cr.line_to(320, 204)
    cr.stroke()
    for x in (206, 378):  # windows
        rgb(1, 1, 1)
        cr.rectangle(x - 5, 265, 66, 66)
        cr.fill()
        rgb(1, 0.88, 0.5)
        cr.rectangle(x, 270, 56, 56)
        cr.fill()
        rgb(1, 1, 1)
        cr.set_line_width(4)
        cr.move_to(x + 28, 270)
        cr.line_to(x + 28, 326)
        cr.move_to(x, 298)
        cr.line_to(x + 56, 298)
        cr.stroke()
        rgb(0.45, 0.28, 0.16)  # flower box
        cr.rectangle(x - 7, 331, 70, 12)
        cr.fill()
        for i, c in enumerate(((0.9, 0.2, 0.3), (1, 0.8, 0.2), (0.9, 0.2, 0.3), (1, 0.8, 0.2))):
            rgb(*c)
            disc(x + 6 + i * 15, 328, 6)
    rgb(0.40, 0.25, 0.14)  # door
    cr.move_to(290, 392)
    cr.line_to(290, 318)
    cr.arc(320, 318, 30, math.pi, 2 * math.pi)
    cr.line_to(350, 392)
    cr.close_path()
    cr.fill()
    rgb(0.52, 0.34, 0.20)
    cr.rectangle(299, 334, 42, 58)
    cr.fill()
    rgb(1, 0.85, 0.3)
    disc(334, 364, 3.5)
    return Gdk.pixbuf_get_from_surface(surf, 0, 0, w, h)


# ------------------------------------------------------------------ Christmas artwork
XMAS_RED, XMAS_GOLD = (0.84, 0.15, 0.18), (1.0, 0.82, 0.32)
XMAS_LIGHTS = ((1.0, 0.27, 0.27), (1.0, 0.82, 0.3), (0.32, 0.9, 0.48), (0.36, 0.66, 1.0))


def _glow(cr, x, y, r, color, alpha):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *color, alpha)
    g.add_color_stop_rgba(1, *color, 0)
    cr.set_source(g)
    cr.arc(x, y, r, 0, 2 * math.pi)
    cr.fill()


def _bulb(cr, x, y, r, color, on):
    """A string-light bulb; on = 0..1 is how bright it is."""
    _glow(cr, x, y, r * 3.6, color, 0.55 * on)
    k = 0.45 + 0.55 * on
    cr.set_source_rgb(*(c * k + 0.08 * (1 - k) for c in color))
    cr.arc(x, y, r, 0, 2 * math.pi)
    cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.6 * on)
    cr.arc(x - r * 0.3, y - r * 0.3, r * 0.34, 0, 2 * math.pi)
    cr.fill()


def _light_swag(cr, x0, y0, x1, y1, sag, t, n, speed=0.5, phase=0.0, r=3.4):
    """A string of Christmas lights hanging between two points; the bulbs twinkle in a chase."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2 + sag * 2  # control point of the curve (it sags by about `sag`)
    pts = []
    for i in range(29):
        u = i / 28
        a, b, c = (1 - u) ** 2, 2 * (1 - u) * u, u * u
        pts.append((a * x0 + b * mx + c * x1, a * y0 + b * my + c * y1))
    cr.set_source_rgb(0.04, 0.17, 0.1)
    cr.set_line_width(2)
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.stroke()
    for i in range(n):
        px, py = pts[int((i + 0.5) / n * 28)]
        cr.set_source_rgb(0.04, 0.17, 0.1)
        cr.rectangle(px - 1.3, py, 2.6, r * 0.9)
        cr.fill()
        on = 0.3 + 0.7 * max(0.0, math.sin(t * (1.5 + 2.4 * speed) - i * 0.85 + phase))
        _bulb(cr, px, py + r * 1.7, r, XMAS_LIGHTS[i % 4], on)


def _star5(cr, x, y, ro, ri):
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = ro if i % 2 == 0 else ri
        (cr.move_to if i == 0 else cr.line_to)(x + rr * math.cos(a), y + rr * math.sin(a))
    cr.close_path()


def _xmas_tree(cr, x, base, s, t, phase=0.0):
    """A decorated tree: x = centre, base = ground, s = height."""
    cr.set_source_rgb(0.33, 0.2, 0.1)
    cr.rectangle(x - s * 0.045, base - s * 0.15, s * 0.09, s * 0.15)
    cr.fill()
    for hw, y_bot, y_top in ((0.30, 0.14, 0.50), (0.24, 0.36, 0.72), (0.17, 0.58, 0.93)):
        xl, xr, yb, yt = x - hw * s, x + hw * s, base - y_bot * s, base - y_top * s
        g = cairo.LinearGradient(xl, 0, xr, 0)
        g.add_color_stop_rgb(0, 0.11, 0.52, 0.29)
        g.add_color_stop_rgb(0.55, 0.06, 0.38, 0.21)
        g.add_color_stop_rgb(1, 0.03, 0.24, 0.14)
        cr.set_source(g)
        cr.move_to(x, yt)
        cr.line_to(xl, yb)
        cr.curve_to(x - hw * s * 0.5, yb - s * 0.05, x + hw * s * 0.5, yb - s * 0.05, xr, yb)
        cr.close_path()
        cr.fill()
        cr.set_source_rgba(*XMAS_GOLD, 0.85)  # gold garland
        cr.set_line_width(max(1.0, s * 0.012))
        cr.move_to(xl + hw * s * 0.18, yb - (yb - yt) * 0.2)
        cr.curve_to(x - hw * s * 0.3, yb - (yb - yt) * 0.05, x + hw * s * 0.3, yb - (yb - yt) * 0.5, xr - hw * s * 0.2, yb - (yb - yt) * 0.28)
        cr.stroke()
        cr.set_source_rgba(1, 1, 1, 0.92)  # snow on the lower tips
        for sx in (xl + hw * s * 0.12, xr - hw * s * 0.12):
            cr.save()
            cr.translate(sx, yb - s * 0.015)
            cr.scale(s * 0.06, s * 0.022)
            cr.arc(0, 0, 1, 0, 2 * math.pi)
            cr.restore()
            cr.fill()
    orn = ((-0.16, 0.20, 0), (0.10, 0.24, 1), (-0.02, 0.33, 3), (-0.11, 0.43, 1), (0.12, 0.47, 0), (0.0, 0.58, 2), (-0.05, 0.66, 0),
           (0.07, 0.73, 3), (0.0, 0.83, 1))
    for i, (dx, dy, c) in enumerate(orn):
        on = 0.35 + 0.65 * max(0.0, math.sin(t * 2.6 + i * 1.7 + phase))
        _bulb(cr, x + dx * s, base - dy * s, s * 0.02, XMAS_LIGHTS[c], on)
    pulse = 0.75 + 0.25 * math.sin(t * 3 + phase)
    _glow(cr, x, base - 0.95 * s, s * 0.2, XMAS_GOLD, 0.6 * pulse)
    _star5(cr, x, base - 0.955 * s, s * 0.075, s * 0.034)
    cr.set_source_rgb(*XMAS_GOLD)
    cr.fill()


def _xmas_gift(cr, x, base, s, body, ribbon):
    """A wrapped present: x = centre, base = ground, s = width."""
    w, h = s, s * 0.78
    x0, y0 = x - w / 2, base - h
    g = cairo.LinearGradient(x0, 0, x0 + w, 0)
    g.add_color_stop_rgb(0, *(min(1, c * 1.15) for c in body))
    g.add_color_stop_rgb(1, *(c * 0.75 for c in body))
    cr.set_source(g)
    cr.rectangle(x0, y0, w, h)
    cr.fill()
    cr.set_source_rgb(*(c * 0.85 for c in body))  # lid
    cr.rectangle(x0 - s * 0.04, y0, w + s * 0.08, h * 0.24)
    cr.fill()
    cr.set_source_rgb(*ribbon)
    cr.rectangle(x - s * 0.085, y0, s * 0.17, h)
    cr.fill()
    cr.set_line_width(s * 0.055)
    for sx in (-1, 1):  # bow
        cr.save()
        cr.translate(x, y0 - s * 0.01)
        cr.rotate(sx * 0.5)
        cr.scale(1, 0.62)
        cr.arc(sx * s * 0.15, -s * 0.08, s * 0.14, 0, 2 * math.pi)
        cr.restore()
        cr.stroke()
    cr.arc(x, y0 - s * 0.02, s * 0.06, 0, 2 * math.pi)
    cr.fill()


def _snowman(cr, x, base, s, t):
    """x = centre, base = ground, s = height."""
    cr.save()
    cr.translate(x, base)
    cr.rotate(math.sin(t * 1.3) * 0.025)
    for cy, rr in ((-0.2, 0.2), (-0.5, 0.15), (-0.73, 0.115)):
        g = cairo.RadialGradient(-rr * s * 0.3, (cy - rr * 0.3) * s, rr * s * 0.1, 0, cy * s, rr * s)
        g.add_color_stop_rgb(0, 1, 1, 1)
        g.add_color_stop_rgb(1, 0.76, 0.85, 0.96)
        cr.set_source(g)
        cr.arc(0, cy * s, rr * s, 0, 2 * math.pi)
        cr.fill()
    cr.set_source_rgb(0.35, 0.2, 0.1)  # arms
    cr.set_line_width(s * 0.022)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    for sx in (-1, 1):
        cr.move_to(sx * s * 0.13, -0.52 * s)
        cr.line_to(sx * s * 0.34, -(0.62 + 0.05 * math.sin(t * 2 + sx)) * s)
        cr.stroke()
    cr.set_source_rgb(*XMAS_RED)  # scarf
    _rounded(cr, -s * 0.14, -0.64 * s, s * 0.28, s * 0.06, s * 0.03)
    cr.fill()
    cr.move_to(s * 0.07, -0.6 * s)
    cr.line_to(s * 0.14 + math.sin(t * 2.5) * s * 0.02, -0.47 * s)
    cr.line_to(s * 0.07, -0.47 * s)
    cr.close_path()
    cr.fill()
    cr.set_source_rgb(0.08, 0.08, 0.1)  # hat
    cr.save()
    cr.translate(0, -0.835 * s)
    cr.scale(s * 0.14, s * 0.022)
    cr.arc(0, 0, 1, 0, 2 * math.pi)
    cr.restore()
    cr.fill()
    cr.rectangle(-s * 0.085, -0.93 * s, s * 0.17, s * 0.1)
    cr.fill()
    cr.set_source_rgb(*XMAS_RED)
    cr.rectangle(-s * 0.085, -0.865 * s, s * 0.17, s * 0.03)
    cr.fill()
    cr.set_source_rgb(0.05, 0.05, 0.07)  # eyes, buttons
    for ex in (-0.04, 0.04):
        cr.arc(ex * s, -0.755 * s, s * 0.011, 0, 2 * math.pi)
        cr.fill()
    for by in (-0.5, -0.43, -0.3):
        cr.arc(0, by * s, s * 0.013, 0, 2 * math.pi)
        cr.fill()
    cr.set_source_rgb(1, 0.52, 0.1)  # carrot
    cr.move_to(0, -0.74 * s)
    cr.line_to(s * 0.11, -0.722 * s)
    cr.line_to(0, -0.71 * s)
    cr.close_path()
    cr.fill()
    cr.restore()


def _leaf(cr, ang, ln, wd, color):
    cr.save()
    cr.rotate(ang)
    cr.move_to(0, 0)
    cr.curve_to(ln * 0.3, -wd, ln * 0.7, -wd * 0.8, ln, 0)
    cr.curve_to(ln * 0.7, wd * 0.8, ln * 0.3, wd, 0, 0)
    cr.set_source_rgb(*color)
    cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.25)
    cr.set_line_width(max(0.8, ln * 0.02))
    cr.move_to(0, 0)
    cr.line_to(ln * 0.92, 0)
    cr.stroke()
    cr.restore()


def _holly(cr, x, y, s, flip=1):
    """A sprig of holly: two leaves and red berries. s = leaf length."""
    cr.save()
    cr.translate(x, y)
    cr.scale(flip, 1)
    _leaf(cr, math.radians(-150), s, s * 0.28, (0.05, 0.33, 0.17))
    _leaf(cr, math.radians(-30), s, s * 0.28, (0.09, 0.43, 0.22))
    _leaf(cr, math.radians(95), s * 0.8, s * 0.24, (0.06, 0.37, 0.19))
    for bx, by in ((-0.07, 0.03), (0.08, 0.02), (0.0, 0.12)):
        g = cairo.RadialGradient(bx * s - s * 0.025, by * s - s * 0.025, 0, bx * s, by * s, s * 0.11)
        g.add_color_stop_rgb(0, 1, 0.5, 0.5)
        g.add_color_stop_rgb(0.5, *XMAS_RED)
        g.add_color_stop_rgb(1, 0.5, 0.05, 0.08)
        cr.set_source(g)
        cr.arc(bx * s, by * s, s * 0.1, 0, 2 * math.pi)
        cr.fill()
    cr.restore()


def _hang_bauble(cr, x, y, length, r, color, t, phase=0.0):
    bx, by = x + math.sin(t * 1.5 + phase) * r * 0.35, y + length
    cr.set_source_rgba(*XMAS_GOLD, 0.8)
    cr.set_line_width(1.2)
    cr.move_to(x, y)
    cr.line_to(bx, by - r * 1.15)
    cr.stroke()
    cr.set_source_rgb(*XMAS_GOLD)
    cr.rectangle(bx - r * 0.28, by - r * 1.3, r * 0.56, r * 0.32)
    cr.fill()
    g = cairo.RadialGradient(bx - r * 0.35, by - r * 0.4, r * 0.1, bx, by, r)
    g.add_color_stop_rgb(0, *(min(1, c * 0.5 + 0.55) for c in color))
    g.add_color_stop_rgb(0.5, *color)
    g.add_color_stop_rgb(1, *(c * 0.45 for c in color))
    cr.set_source(g)
    cr.arc(bx, by, r, 0, 2 * math.pi)
    cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.7)
    cr.save()
    cr.translate(bx - r * 0.35, by - r * 0.4)
    cr.rotate(-0.7)
    cr.scale(r * 0.22, r * 0.12)
    cr.arc(0, 0, 1, 0, 2 * math.pi)
    cr.restore()
    cr.fill()


def _snowfall(cr, x0, y0, w, h, t, speed, count=40, seed=1, size=1.0):
    rnd = random.Random(seed)
    for _ in range(count):
        fx, fy, vy, sz, ph = rnd.random(), rnd.random(), rnd.uniform(0.05, 0.14), rnd.uniform(0.9, 2.6), rnd.uniform(0, 6.3)
        y = (fy + t * vy * (0.4 + speed)) % 1.0
        x = (fx + math.sin(t * 0.8 + ph) * 0.02) % 1.0
        cr.set_source_rgba(1, 1, 1, 0.5 + 0.4 * sz / 2.6)
        cr.arc(x0 + x * w, y0 + y * h, sz * size, 0, 2 * math.pi)
        cr.fill()


def _snow_ground(cr, w, h, pad, t):
    top = h - pad * 0.34
    g = cairo.LinearGradient(0, top - 8, 0, h)
    g.add_color_stop_rgb(0, 0.98, 0.99, 1)
    g.add_color_stop_rgb(1, 0.72, 0.82, 0.94)
    cr.set_source(g)
    cr.move_to(0, h)
    for i in range(0, int(w) + 8, 8):
        cr.line_to(i, top + 5 * math.sin(i * 0.033) + 3.5 * math.sin(i * 0.09 + 1))
    cr.line_to(w, h)
    cr.close_path()
    cr.fill()
    rnd = random.Random(4)
    for _ in range(int(w / 28)):  # glitter
        tw = 0.5 + 0.5 * math.sin(t * 3 + rnd.uniform(0, 6.3))
        cr.set_source_rgba(1, 1, 1, 0.3 + 0.6 * tw)
        cr.arc(rnd.uniform(0, w), rnd.uniform(top + 4, h - 3), 1 + tw, 0, 2 * math.pi)
        cr.fill()


def _candy_ring(cr, cx, cy, r, t):
    """A candy-cane ring around the menu disc; the stripes turn slowly."""
    lw = 8
    cr.set_source_rgba(0.25, 0.04, 0.05, 0.5)
    cr.set_line_width(lw + 3)
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.stroke()
    cr.set_source_rgb(0.98, 0.97, 0.95)
    cr.set_line_width(lw)
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.stroke()
    seg = 2 * math.pi * r / 64
    cr.set_dash([seg / 2, seg / 2], (t * seg * 0.7) % seg)
    cr.set_source_rgb(0.85, 0.12, 0.16)
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.stroke()
    cr.set_dash([])
    cr.set_source_rgba(1, 1, 1, 0.45)
    cr.set_line_width(1.6)
    cr.arc(cx, cy, r - lw * 0.22, math.pi * 1.12, math.pi * 1.7)
    cr.stroke()


def santa_hat(cr, x, y, r, tilt=0.0, t=0.0):
    """A Santa hat; (x, y) = middle of the white brim, r = half the brim width, tilt in radians."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(tilt)
    sway = math.sin(t * 2) * r * 0.05
    g = cairo.LinearGradient(-r, 0, r * 1.2, 0)
    g.add_color_stop_rgb(0, 0.9, 0.18, 0.2)
    g.add_color_stop_rgb(1, 0.62, 0.08, 0.12)
    cr.set_source(g)
    cr.move_to(-r * 0.82, 0)
    cr.curve_to(-r * 0.75, -r * 1.0, -r * 0.05, -r * 1.9, r * 0.75, -r * 1.65)
    cr.curve_to(r * 0.98, -r * 1.58, r * 1.15 + sway, -r * 1.25, r * 1.1 + sway, -r * 0.98)
    cr.curve_to(r * 0.98, -r * 0.55, r * 0.9, -r * 0.3, r * 0.82, 0)
    cr.close_path()
    cr.fill()
    _glow(cr, r * 1.1 + sway, -r * 0.92, r * 0.5, (1, 1, 1), 0.25)
    cr.set_source_rgb(1, 1, 1)  # pompom
    cr.arc(r * 1.1 + sway, -r * 0.92, r * 0.21, 0, 2 * math.pi)
    cr.fill()
    cr.set_source_rgb(0.98, 0.98, 1)  # fur brim
    _rounded(cr, -r * 0.98, -r * 0.2, r * 1.96, r * 0.42, r * 0.21)
    cr.fill()
    cr.set_source_rgba(0.75, 0.8, 0.9, 0.55)
    for i in range(6):
        cr.arc(-r * 0.78 + i * r * 0.31, r * 0.02 + (i % 2) * r * 0.08, r * 0.045, 0, 2 * math.pi)
        cr.fill()
    cr.restore()


def _xmas_disc(cr, cx, cy, r, t, speed, opacity):
    """Inside the menu disc: pine-green night with gold stars, a warm glow and falling snow."""
    g = cairo.RadialGradient(cx, cy - r * 0.25, 0, cx, cy, r)
    g.add_color_stop_rgba(0, 0.08, 0.3, 0.21, opacity)
    g.add_color_stop_rgba(0.65, 0.04, 0.17, 0.13, opacity)
    g.add_color_stop_rgba(1, 0.02, 0.07, 0.08, opacity)
    cr.set_source(g)
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.fill()
    _glow(cr, cx, cy + r * 0.9, r * 0.95, (1.0, 0.42, 0.2), 0.2)
    _sparkles(cr, cx, cy, r, t, speed, color=XMAS_GOLD, count=26, seed=21)
    _snowfall(cr, cx - r, cy - r, 2 * r, 2 * r, t, speed, count=48, seed=5)


def _xmas_frame(cr, pad, w, h, cx, cy, r_disc, t, speed):
    """Around the menu: lights, hanging baubles, holly, tree, snowman and presents on the snow, a candy-cane ring, a Santa hat."""
    cr.save()  # snow outside the disc
    cr.rectangle(0, 0, w, h)
    cr.arc(cx, cy, r_disc, 0, 2 * math.pi)
    cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    cr.clip()
    _snowfall(cr, 0, 0, w, h, t, speed, count=70, seed=8, size=1.1)
    cr.restore()
    _snow_ground(cr, w, h, pad, t)
    base = h - pad * 0.1
    _xmas_tree(cr, pad * 0.95, base, pad * 2.0, t)
    _snowman(cr, w - pad * 0.85, base, pad * 1.55, t)
    _xmas_gift(cr, pad * 1.95, base + 2, pad * 0.5, (0.85, 0.15, 0.2), (1.0, 0.85, 0.35))
    _xmas_gift(cr, pad * 2.55, base + 3, pad * 0.36, (0.15, 0.5, 0.82), (1, 1, 1))
    _xmas_gift(cr, w - pad * 2.0, base + 2, pad * 0.46, (0.1, 0.55, 0.3), (0.95, 0.2, 0.25))
    _candy_ring(cr, cx, cy, r_disc + 3, t)
    _light_swag(cr, 0, pad * 0.12, w / 2, pad * 0.08, pad * 0.34, t, 12, speed, 0.0)
    _light_swag(cr, w / 2, pad * 0.08, w, pad * 0.12, pad * 0.34, t, 12, speed, 1.4)
    _hang_bauble(cr, w * 0.2, pad * 0.1, pad * 0.62, pad * 0.17, (0.85, 0.15, 0.2), t, 0)
    _hang_bauble(cr, w * 0.8, pad * 0.1, pad * 0.5, pad * 0.15, (0.2, 0.45, 0.85), t, 2)
    _hang_bauble(cr, w * 0.5, pad * 0.1, pad * 0.7, pad * 0.18, XMAS_GOLD, t, 4)
    _holly(cr, pad * 0.42, pad * 0.62, pad * 0.5)
    _holly(cr, w - pad * 0.42, pad * 0.62, pad * 0.5, -1)
    a = math.radians(-52)  # a Santa hat on the rim of the disc
    santa_hat(cr, cx + (r_disc + 2) * math.cos(a), cy + (r_disc + 2) * math.sin(a), r_disc * 0.15, a + math.pi / 2 + 0.1, t)


def _xmas_osd_frame(cr, pad, w, h, t, speed):
    """Around the little message box: lights, a Santa hat, holly, a tiny tree and a present on the snow."""
    bx, by, bw, bh = pad, pad, w - 2 * pad, h - 2 * pad
    _snowfall(cr, 0, 0, w, h, t, speed, count=24, seed=12)
    _light_swag(cr, bx + 6, by - 2, bx + bw - 6, by - 2, pad * 0.3, t, 10, speed, 0.5, r=3.0)
    base = by + bh + pad * 0.7
    cr.save()
    _rounded(cr, bx - pad * 0.3, by + bh + pad * 0.1, bw + pad * 0.6, pad * 0.95, 14)
    cr.clip()
    _snow_ground(cr, w, h, pad * 1.6, t)
    cr.restore()
    _xmas_tree(cr, pad * 0.5, base, pad * 1.6, t, 1.0)
    _xmas_gift(cr, bx + bw - pad * 0.7, base + 1, pad * 0.5, (0.85, 0.15, 0.2), (1.0, 0.85, 0.35))
    _holly(cr, bx + bw - pad * 0.1, by + pad * 0.15, pad * 0.42, -1)
    santa_hat(cr, bx + pad * 0.9, by - pad * 0.02, pad * 0.36, -0.25, t)

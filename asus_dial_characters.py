"""The welcome scene of the ASUS Dial: a character walks in, waves, "writes" a message in a speech bubble
and walks out. No voice and no sounds.

Shared by asus-dial-welcome (the real thing, shown at login) and asus-dial-manager (live preview).
Characters: human, robot, skeleton, or your own PNG. They can take a color, a rainbow style (when the
theme is rainbow or the option is on) and a Halloween look (witch hat, ghost, bats) when the theme is Halloween.
"""
import colorsys
import math
import os

import gi

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo
import cairo

import asus_dial_config as acfg
import asus_dial_theme as ath

CHARACTERS = ("human", "robot", "skeleton", "image")
DEFAULT_MESSAGES = {"en": "Welcome to the PC, {name}!", "es": "¡Bienvenido al PC, {name}!", "it": "Benvenuto al PC, {name}!"}
DEFAULT_NAME = "User"
TYPE_CPS = 16.0  # letters per second
T_WALK_IN, T_WAVE, T_BUBBLE, T_TYPE = 2.4, 2.8, 3.2, 3.6
HOLD_S, BOW_S, WALK_OUT_S = 3.5, 0.8, 2.6


def resolve_message(cfg, lang):
    w = cfg.get("welcome", {})
    template = (w.get("message") or "").strip() or DEFAULT_MESSAGES.get(lang, DEFAULT_MESSAGES["en"])
    name = (w.get("name") or "").strip() or DEFAULT_NAME
    try:
        return template.format(name=name)
    except (KeyError, IndexError, ValueError):
        return template.replace("{name}", name)


def _hsv(h, s=0.8, v=1.0):
    return colorsys.hsv_to_rgb(h % 1.0, s, v)


def _ease_out(u):
    return 1 - (1 - u) ** 3


def _ease_back(u):
    c1 = 1.70158
    return 1 + (c1 + 1) * (u - 1) ** 3 + c1 * (u - 1) ** 2


def _limb(cr, pts, width, color, outline=(0.1, 0.08, 0.15)):
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    for col, w in ((outline, width * 1.28), (color, width)):
        cr.set_source_rgb(*col)
        cr.set_line_width(w)
        cr.move_to(*pts[0])
        for p in pts[1:]:
            cr.line_to(*p)
        cr.stroke()


def _ellipse(cr, x, y, rx, ry):
    cr.save()
    cr.translate(x, y)
    cr.scale(rx, ry)
    cr.arc(0, 0, 1, 0, 2 * math.pi)
    cr.restore()


def _witch_hat(cr, x, y, r):
    """x, y = where the hat sits on the head (centre of the brim), r = brim radius."""
    cr.save()
    cr.translate(x, y)
    cr.set_source_rgb(0.1, 0.05, 0.16)
    cr.move_to(-r * 0.62, 0)
    cr.curve_to(-r * 0.4, -r * 0.7, -r * 0.2, -r * 1.2, r * 0.2, -r * 1.9)
    cr.curve_to(r * 0.35, -r * 1.3, r * 0.55, -r * 0.5, r * 0.62, 0)
    cr.close_path()
    cr.fill()
    cr.set_source_rgb(1.0, 0.5, 0.05)
    cr.rectangle(-r * 0.6, -r * 0.3, r * 1.2, r * 0.22)
    cr.fill()
    _ellipse(cr, 0, 0, r, r * 0.22)
    cr.set_source_rgb(0.1, 0.05, 0.16)
    cr.fill()
    cr.restore()


def _party_hat(cr, hat, x, y, r, t):
    """The hat of the season: a Santa hat for Christmas (hat == "santa"), a witch hat otherwise."""
    if hat == "santa":
        ath.santa_hat(cr, x, y + r * 0.1, r * 0.95, -0.12, t)
    else:
        _witch_hat(cr, x, y, r)


# ------------------------------------------------------------------ characters (feet at 0, 0; height H; y points up as negative)
def draw_human(cr, H, t, st, color, rainbow, hat, curly=False):
    walk = st["walk"]
    sw = math.sin(t * 9) * 0.5 if walk else 0.0
    bob = abs(math.sin(t * 9)) * H * 0.018 if walk else math.sin(t * 2) * H * 0.004
    jeans, skin, hair = (0.16, 0.2, 0.34), (0.98, 0.8, 0.64), (0.2, 0.12, 0.08)
    shirt = _hsv(t * 0.25) if rainbow else ath.rgb(color)
    cr.save()
    cr.translate(0, -bob)
    for side in (-1, 1):  # legs and shoes
        a = sw * side
        hx, hy, L = side * H * 0.055, -H * 0.42, H * 0.42
        fx, fy = hx + math.sin(a) * L, hy + math.cos(a) * L
        _limb(cr, [(hx, hy), (fx, fy)], H * 0.085, jeans)
        _ellipse(cr, fx + H * 0.015, fy - H * 0.005, H * 0.075, H * 0.038)
        cr.set_source_rgb(0.97, 0.97, 0.97)
        cr.fill_preserve()
        cr.set_source_rgb(0.1, 0.08, 0.15)
        cr.set_line_width(H * 0.008)
        cr.stroke()
    cr.save()  # upper body (bows from the hip)
    cr.translate(0, -H * 0.42)
    cr.rotate(st["bow"] * 0.55)
    cr.translate(0, H * 0.42)
    for side in (-1, 1):  # arms
        sx, sy = side * H * 0.16, -H * 0.7
        if side == 1 and st["wave"]:
            ex, ey = sx + H * 0.1, sy - H * 0.13
            wv = math.sin(t * 11) * 0.6
            hx2, hy2 = ex + H * 0.15 * math.sin(wv), ey - H * 0.15 * math.cos(wv)
            _limb(cr, [(sx, sy), (ex, ey), (hx2, hy2)], H * 0.075, shirt)
        else:
            a = (-sw * side * 0.9) if walk else side * 0.1
            hx2, hy2 = sx + math.sin(a) * H * 0.3, sy + math.cos(a) * H * 0.3
            _limb(cr, [(sx, sy), (hx2, hy2)], H * 0.075, shirt)
        cr.arc(hx2, hy2, H * 0.042, 0, 2 * math.pi)
        cr.set_source_rgb(*skin)
        cr.fill_preserve()
        cr.set_source_rgb(0.1, 0.08, 0.15)
        cr.set_line_width(H * 0.008)
        cr.stroke()
    ath._rounded(cr, -H * 0.155, -H * 0.76, H * 0.31, H * 0.36, H * 0.07)  # torso (hoodie)
    g = cairo.LinearGradient(0, -H * 0.76, 0, -H * 0.4)
    g.add_color_stop_rgb(0, *[min(1, c + 0.18) for c in shirt])
    g.add_color_stop_rgb(1, *[max(0, c - 0.12) for c in shirt])
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgb(0.1, 0.08, 0.15)
    cr.set_line_width(H * 0.01)
    cr.stroke()
    ath._rounded(cr, -H * 0.075, -H * 0.55, H * 0.15, H * 0.07, H * 0.025)  # pocket
    cr.set_source_rgba(0, 0, 0, 0.18)
    cr.fill()
    cr.set_source_rgb(*skin)  # neck
    cr.rectangle(-H * 0.035, -H * 0.8, H * 0.07, H * 0.06)
    cr.fill()
    hy = -H * 0.9  # head
    cr.arc(0, hy, H * 0.125, 0, 2 * math.pi)
    cr.set_source_rgb(*skin)
    cr.fill_preserve()
    cr.set_source_rgb(0.1, 0.08, 0.15)
    cr.set_line_width(H * 0.01)
    cr.stroke()
    cr.set_source_rgb(*hair)  # hair
    if curly:  # a crown of curls
        cr.arc(0, hy - H * 0.01, H * 0.128, math.pi * 1.0, math.pi * 2.0)
        cr.fill()
        for i in range(11):
            a = math.pi * (1.0 + i / 10)
            r = H * (0.135 + 0.012 * (i % 2))
            cr.arc(math.cos(a) * r, hy - H * 0.01 + math.sin(a) * r, H * 0.05, 0, 2 * math.pi)
            cr.fill()
        for cx_ in (-0.07, 0.0, 0.07):  # curly fringe
            cr.arc(cx_ * H, hy - H * 0.1, H * 0.04, 0, 2 * math.pi)
            cr.fill()
    else:
        cr.arc(0, hy - H * 0.01, H * 0.133, math.pi * 1.02, math.pi * 1.98)
        cr.curve_to(H * 0.1, hy - H * 0.06, -H * 0.02, hy - H * 0.13, -H * 0.133, hy - H * 0.01)
        cr.fill()
    blink = st["blink"]
    for ex in (-0.045, 0.045):  # eyes
        _ellipse(cr, ex * H, hy, H * 0.017, H * 0.017 * (0.12 if blink else 1))
        cr.set_source_rgb(0.08, 0.06, 0.12)
        cr.fill()
    cr.set_source_rgba(1, 0.4, 0.45, 0.35)  # blush
    for ex in (-0.085, 0.085):
        cr.arc(ex * H, hy + H * 0.035, H * 0.022, 0, 2 * math.pi)
        cr.fill()
    cr.set_source_rgb(0.5, 0.15, 0.2)  # smile
    cr.set_line_width(H * 0.009)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.arc(0, hy + H * 0.015, H * 0.045, math.pi * 0.2, math.pi * 0.8)
    cr.stroke()
    if hat:
        _party_hat(cr, hat, 0, hy - H * 0.085, H * 0.19, t)
    cr.restore()
    cr.restore()


def draw_robot(cr, H, t, st, color, rainbow, hat):
    walk = st["walk"]
    sw = math.sin(t * 9) * 0.4 if walk else 0.0
    bob = abs(math.sin(t * 9)) * H * 0.012 if walk else 0.0
    body = _hsv(t * 0.25, 0.55, 0.95) if rainbow else ath.rgb(color)
    light = [min(1, c + 0.25) for c in body]
    dark = [max(0, c - 0.25) for c in body]
    eye = _hsv(t * 0.5, 0.6, 1.0) if rainbow else (0.3, 1.0, 1.0)
    ink = (0.1, 0.12, 0.18)
    cr.save()
    cr.translate(0, -bob)
    for side in (-1, 1):  # legs: pistons with square feet
        a = sw * side
        hx, hy, L = side * H * 0.07, -H * 0.36, H * 0.33
        fx, fy = hx + math.sin(a) * L * 0.7, hy + math.cos(a) * L
        _limb(cr, [(hx, hy), (fx, fy)], H * 0.07, dark, ink)
        ath._rounded(cr, fx - H * 0.07, fy - H * 0.035, H * 0.14, H * 0.05, H * 0.015)
        cr.set_source_rgb(*dark)
        cr.fill_preserve()
        cr.set_source_rgb(*ink)
        cr.set_line_width(H * 0.008)
        cr.stroke()
    cr.save()
    cr.translate(0, -H * 0.4)
    cr.rotate(st["bow"] * 0.55)
    cr.translate(0, H * 0.4)
    for side in (-1, 1):  # arms with round joints
        sx, sy = side * H * 0.2, -H * 0.66
        if side == 1 and st["wave"]:
            ex, ey = sx + H * 0.09, sy - H * 0.12
            wv = math.sin(t * 11) * 0.6
            hx2, hy2 = ex + H * 0.15 * math.sin(wv), ey - H * 0.15 * math.cos(wv)
            _limb(cr, [(sx, sy), (ex, ey), (hx2, hy2)], H * 0.06, light, ink)
        else:
            a = (-sw * side * 0.9) if walk else side * 0.1
            hx2, hy2 = sx + math.sin(a) * H * 0.27, sy + math.cos(a) * H * 0.27
            _limb(cr, [(sx, sy), (hx2, hy2)], H * 0.06, light, ink)
        cr.arc(hx2, hy2, H * 0.045, 0, 2 * math.pi)
        cr.set_source_rgb(*dark)
        cr.fill_preserve()
        cr.set_source_rgb(*ink)
        cr.set_line_width(H * 0.008)
        cr.stroke()
    ath._rounded(cr, -H * 0.18, -H * 0.72, H * 0.36, H * 0.34, H * 0.05)  # body
    g = cairo.LinearGradient(0, -H * 0.72, 0, -H * 0.38)
    g.add_color_stop_rgb(0, *light)
    g.add_color_stop_rgb(1, *dark)
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgb(*ink)
    cr.set_line_width(H * 0.012)
    cr.stroke()
    ath._rounded(cr, -H * 0.11, -H * 0.62, H * 0.22, H * 0.1, H * 0.02)  # chest panel with blinking lights
    cr.set_source_rgb(*ink)
    cr.fill()
    for i in range(3):
        on = 0.5 + 0.5 * math.sin(t * 5 + i * 2)
        cr.arc(-H * 0.06 + i * H * 0.06, -H * 0.57, H * 0.014, 0, 2 * math.pi)
        cr.set_source_rgba(*(_hsv(t * 0.4 + i * 0.2) if rainbow else (0.3, 1, 0.5)), 0.4 + 0.6 * on)
        cr.fill()
    hy = -H * 0.88  # head
    ath._rounded(cr, -H * 0.15, hy - H * 0.11, H * 0.3, H * 0.22, H * 0.06)
    g = cairo.LinearGradient(0, hy - H * 0.11, 0, hy + H * 0.11)
    g.add_color_stop_rgb(0, *light)
    g.add_color_stop_rgb(1, *body)
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgb(*ink)
    cr.set_line_width(H * 0.012)
    cr.stroke()
    cr.set_source_rgb(*ink)  # antenna
    cr.set_line_width(H * 0.012)
    cr.move_to(0, hy - H * 0.11)
    cr.line_to(0, hy - H * 0.17)
    cr.stroke()
    blinkl = 0.5 + 0.5 * math.sin(t * 8)
    cr.arc(0, hy - H * 0.18, H * 0.02, 0, 2 * math.pi)
    cr.set_source_rgb(1, 0.25 + 0.5 * blinkl, 0.25)
    cr.fill()
    for ex in (-0.06, 0.06):  # glowing eyes
        gl = cairo.RadialGradient(ex * H, hy - H * 0.01, 0, ex * H, hy - H * 0.01, H * 0.06)
        gl.add_color_stop_rgba(0, *eye, 0.9)
        gl.add_color_stop_rgba(1, *eye, 0)
        cr.set_source(gl)
        cr.arc(ex * H, hy - H * 0.01, H * 0.06, 0, 2 * math.pi)
        cr.fill()
        _ellipse(cr, ex * H, hy - H * 0.01, H * 0.028, H * 0.028 * (0.12 if st["blink"] else 1))
        cr.set_source_rgb(0.04, 0.08, 0.14)
        cr.fill()
        _ellipse(cr, ex * H + H * 0.006, hy - H * 0.016, H * 0.014, H * 0.014 * (0.12 if st["blink"] else 1))
        cr.set_source_rgb(*eye)
        cr.fill()
    for i in range(5):  # mouth
        bh = H * (0.012 + 0.012 * abs(math.sin(t * 6 + i)))
        cr.rectangle(-H * 0.05 + i * H * 0.022, hy + H * 0.055 - bh / 2, H * 0.014, bh)
        cr.set_source_rgb(*ink)
        cr.fill()
    if hat:
        _party_hat(cr, hat, 0, hy - H * 0.105, H * 0.19, t)
    cr.restore()
    cr.restore()


def draw_skeleton(cr, H, t, st, color, rainbow, hat):
    bone = _hsv(t * 0.25, 0.35, 1.0) if rainbow else (ath.rgb(color) if color else (0.96, 0.95, 0.88))
    ath._skeleton(cr, 0, 0, H, t, 0.0, bone=bone)
    if hat:
        _party_hat(cr, hat, 0, -H * 0.93, H * 0.17, t)


def draw_claude(cr, H, t, st):
    """A friendly AI mascot: a soft clay-colored blob with a glowing spark on top."""
    bob = math.sin(t * 2.2) * H * 0.012
    clay, light, ink = (0.85, 0.47, 0.34), (0.97, 0.72, 0.56), (0.16, 0.1, 0.1)
    cr.save()
    cr.translate(0, -bob)
    for fx in (-0.1, 0.1):  # little feet
        _ellipse(cr, fx * H, -H * 0.02, H * 0.08, H * 0.04)
        cr.set_source_rgb(*ink)
        cr.fill()
    for side in (-1, 1):  # arms
        sx, sy = side * H * 0.24, -H * 0.42
        if side == 1 and st["wave"]:
            wv = math.sin(t * 11) * 0.5
            ex, ey = sx + H * 0.14, sy - H * 0.2
            _limb(cr, [(sx, sy), (ex + math.sin(wv) * H * 0.03, ey - math.cos(wv) * H * 0.03)], H * 0.07, clay, ink)
        else:
            _limb(cr, [(sx, sy), (sx + side * H * 0.08, sy + H * 0.16)], H * 0.07, clay, ink)
    _ellipse(cr, 0, -H * 0.4, H * 0.27, H * 0.35)  # body
    g = cairo.RadialGradient(-H * 0.08, -H * 0.55, H * 0.03, 0, -H * 0.4, H * 0.38)
    g.add_color_stop_rgb(0, *light)
    g.add_color_stop_rgb(1, *clay)
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgb(*ink)
    cr.set_line_width(H * 0.012)
    cr.stroke()
    for ex in (-0.09, 0.09):  # eyes
        _ellipse(cr, ex * H, -H * 0.46, H * 0.028, H * 0.05 * (0.12 if st["blink"] else 1))
        cr.set_source_rgb(*ink)
        cr.fill()
    cr.set_source_rgb(*ink)  # smile
    cr.set_line_width(H * 0.012)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.arc(0, -H * 0.4, H * 0.07, math.pi * 0.15, math.pi * 0.85)
    cr.stroke()
    cr.set_source_rgba(1, 0.5, 0.45, 0.35)  # cheeks
    for ex in (-0.15, 0.15):
        cr.arc(ex * H, -H * 0.38, H * 0.03, 0, 2 * math.pi)
        cr.fill()
    cx, cy, r = 0, -H * 0.86, H * 0.1  # the spark
    gl = cairo.RadialGradient(cx, cy, 0, cx, cy, r * 2.2)
    gl.add_color_stop_rgba(0, 1, 0.8, 0.45, 0.8)
    gl.add_color_stop_rgba(1, 1, 0.8, 0.45, 0)
    cr.set_source(gl)
    cr.arc(cx, cy, r * 2.2, 0, 2 * math.pi)
    cr.fill()
    cr.save()
    cr.translate(cx, cy)
    cr.rotate(t * 0.8)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_width(r * 0.28)
    cr.set_source_rgb(0.95, 0.5, 0.25)
    for i in range(8):
        a = i * math.pi / 4
        cr.move_to(math.cos(a) * r * 0.25, math.sin(a) * r * 0.25)
        cr.line_to(math.cos(a) * r, math.sin(a) * r)
    cr.stroke()
    cr.restore()
    cr.restore()


def _say(cr, text, tip_x, tip_y, px, t_local, w_max, fill, border, tcol, cps=14.0):
    """A speech bubble whose tail tip is at (tip_x, tip_y); the text is typed letter by letter."""
    layout = PangoCairo.create_layout(cr)
    fd = Pango.FontDescription("Sans Bold")
    fd.set_absolute_size(px * Pango.SCALE)
    layout.set_font_description(fd)
    layout.set_text(text, -1)
    tw, th = layout.get_pixel_size()
    padx, pady = px * 0.7, px * 0.5
    bw, bh = tw + 2 * padx, th + 2 * pady
    bx = max(4, min(w_max - bw - 4, tip_x - bw * 0.3))
    by = tip_y - px * 1.2 - bh
    pop = _ease_back(max(0.0, min(1.0, t_local / 0.3)))
    cr.save()
    cr.translate(tip_x, tip_y)
    cr.scale(pop, pop)
    cr.translate(-tip_x, -tip_y)
    ath._rounded(cr, bx, by, bw, bh, px * 0.8)
    cr.move_to(tip_x - px * 0.5, by + bh - 2)
    cr.line_to(tip_x, tip_y)
    cr.line_to(tip_x + px * 0.5, by + bh - 2)
    cr.set_source_rgba(*fill)
    cr.fill_preserve()
    cr.set_source_rgb(*border)
    cr.set_line_width(max(2.0, px * 0.1))
    cr.stroke()
    n = int(max(0.0, t_local - 0.3) * cps)
    layout.set_text(text[:n] + ("▌" if n < len(text) else ""), -1)
    cr.set_source_rgb(*tcol)
    cr.move_to(bx + padx, by + pady)
    PangoCairo.show_layout(cr, layout)
    cr.restore()


DUO_PERIOD = 9.0


def draw_duo(cr, t, w, h, say_human, say_ai, theme=None):
    """Ale (a human with red clothes and curly hair) and Claude (an AI) greet each other in speech bubbles."""
    t = t % DUO_PERIOD
    H, ground = h * 0.5, h * 0.94
    st_h = {"walk": False, "wave": 0.4 < t < 3.6, "blink": (t % 2.8) < 0.13, "bow": 0.0}
    st_c = {"walk": False, "wave": 3.2 < t < 7.0, "blink": ((t + 1.1) % 3.1) < 0.13, "bow": 0.0}
    cr.save()
    cr.translate(w * 0.27, ground)
    draw_human(cr, H, t, st_h, "#e02424", False, False, curly=True)
    cr.restore()
    cr.save()
    cr.translate(w * 0.73, ground)
    draw_claude(cr, H, t, st_c)
    cr.restore()
    fill, border, tcol = (1, 1, 1, 0.97), (0.2, 0.2, 0.3), (0.1, 0.1, 0.18)
    fade = 1.0 if t < DUO_PERIOD - 0.6 else max(0.0, (DUO_PERIOD - t) / 0.6)
    px = max(12.0, h * 0.075)
    cr.push_group()
    if t >= 0.6:
        _say(cr, say_human, w * 0.27 + H * 0.12, ground - H * 1.13, px, t - 0.6, w, fill, (0.85, 0.15, 0.15), tcol)
    if t >= 3.4:
        _say(cr, say_ai, w * 0.73 - H * 0.05, ground - H * 1.1, px, t - 3.4, w, fill, (0.9, 0.5, 0.25), tcol)
    cr.pop_group_to_source()
    cr.paint_with_alpha(fade)


def draw_image(cr, H, t, st, surf):
    if surf is None:
        return
    sc = H / surf.get_height()
    walk = st["walk"]
    hop = abs(math.sin(t * 9)) * H * 0.04 if walk else 0.0
    cr.save()
    cr.translate(0, -hop)
    tilt = (math.sin(t * 9) * 0.06 if walk else 0.0) + (math.sin(t * 10) * 0.07 if st["wave"] else 0.0) + st["bow"] * 0.5
    cr.rotate(tilt)
    cr.scale(sc, sc)
    cr.set_source_surface(surf, -surf.get_width() / 2, -surf.get_height())
    cr.paint()
    cr.restore()


def _rainbow_arc(cr, cx, cy, r, alpha):
    band = r * 0.075
    cr.set_line_width(band * 1.05)
    for i in range(7):
        cr.arc(cx, cy, r - i * band, math.pi, 2 * math.pi)
        cr.set_source_rgba(*_hsv(i / 7 * 0.85, 0.85, 1.0), alpha)
        cr.stroke()


# ------------------------------------------------------------------ the scene
class Welcome:
    """The whole welcome animation. draw(cr, t, w, h) for t in 0..total."""

    def __init__(self, cfg, lang):
        w = cfg.get("welcome", {})
        self.theme = acfg.theme_of(cfg)
        self.character = w.get("character") if w.get("character") in CHARACTERS else "human"
        self.color = w.get("color") or "#4080ff"
        self.rainbow = bool(w.get("rainbow")) or self.theme["bg_type"] == "rainbow"
        self.halloween = self.theme["bg_type"] == "halloween"
        self.christmas = self.theme["bg_type"] == "christmas"
        self.image = None
        if self.character == "image":
            try:
                self.image = cairo.ImageSurface.create_from_png(w.get("image") or "")
            except Exception:
                self.character = "human"
        self.message = resolve_message(cfg, lang)
        self.t_type1 = T_TYPE + len(self.message) / TYPE_CPS
        self.t_bow = self.t_type1 + HOLD_S
        self.t_out = self.t_bow + BOW_S
        self.total = self.t_out + WALK_OUT_S
        self._lines = {}

    # --- text layout
    def _layout(self, cr, px, maxw):
        key = (px, maxw)
        if key in self._lines:
            return self._lines[key]
        layout = PangoCairo.create_layout(cr)
        fd = Pango.FontDescription("Sans Bold")
        fd.set_absolute_size(px * Pango.SCALE)
        layout.set_font_description(fd)

        def width(s):
            layout.set_text(s or " ", -1)
            return layout.get_pixel_size()[0]

        lines, cur = [], ""
        for word in self.message.split(" "):
            cand = (cur + " " + word).strip()
            if cur and width(cand) > maxw:
                lines.append(cur)
                cur = word
            else:
                cur = cand
        lines.append(cur)
        layout.set_text("Ág", -1)
        lh = layout.get_pixel_size()[1]
        res = (lines, lh, max(width(ln) for ln in lines))
        self._lines[key] = res
        return res

    def _bubble_colors(self):
        th = self.theme
        text, accent = ath.theme_colors(th)
        if th["bg_type"] == "plasma":
            return (*ath.plasma_palette(th["plasma_mode"])["bg"], 0.96), accent, text
        if self.halloween:
            return (0.16, 0.05, 0.24, 0.96), accent, text
        if self.christmas:
            return (0.04, 0.2, 0.14, 0.96), accent, text
        if th["bg_type"] in ("rainbow", "image"):
            return (0.08, 0.08, 0.11, 0.94), accent, text
        return (*ath.rgb(th["bg_color"], (0.08, 0.08, 0.1)), max(0.92, th["bg_opacity"])), accent, text

    def draw(self, cr, t, w, h):
        H = h * 0.52
        ground = h * 0.94
        x_stop = H * 0.62
        x0 = -H * 0.45
        face = 1
        walk = False
        if t < T_WALK_IN:
            u = t / T_WALK_IN
            x, walk = x0 + (x_stop - x0) * _ease_out(u), u < 0.97
        elif t < self.t_out:
            x = x_stop
        else:
            u = min(1.0, (t - self.t_out) / WALK_OUT_S)
            x, walk, face = x_stop - (x_stop - x0) * u * u, True, -1
        st = {"walk": walk, "wave": T_WAVE < t < self.t_bow, "blink": (t % 2.6) < 0.13,
              "bow": math.sin(math.pi * max(0.0, min(1.0, (t - self.t_bow) / BOW_S))) if self.t_bow <= t < self.t_out else 0.0}
        cr.save()
        if self.rainbow:  # a rainbow behind the character
            _rainbow_arc(cr, x, ground - H * 0.05, H * 0.95, 0.55)
        if self.halloween:
            sp = self.theme["speed"]
            _ghost_x = x_stop + H * 0.8
            ath._ghost(cr, _ghost_x, ground - H * 0.85, H * 0.28, t, 0.7, 0.85)
            ath._pumpkin(cr, x_stop + H * 1.25, ground, H * 0.3, t, 1)
            for k in range(2):
                u = (t * 0.12 * (0.5 + sp) + k * 0.5) % 1.0
                ath._bat(cr, u * w, h * (0.12 + 0.1 * k) + math.sin(u * 18 + k) * h * 0.02, H * 0.14, t, k * 2)
        if self.christmas:
            sp = self.theme["speed"]
            ath._snowfall(cr, 0, 0, w, h, t, sp, count=60, seed=31, size=1.3)
            ath._xmas_tree(cr, x_stop + H * 1.05, ground, H * 0.95, t)
            ath._xmas_gift(cr, x_stop + H * 0.62, ground, H * 0.2, (0.85, 0.15, 0.2), (1.0, 0.85, 0.35))
            ath._xmas_gift(cr, x_stop + H * 0.82, ground, H * 0.14, (0.15, 0.5, 0.82), (1, 1, 1))
            ath._snowman(cr, x_stop + H * 1.75, ground, H * 0.7, t)
            ath._xmas_gift(cr, x_stop + H * 2.15, ground, H * 0.17, (0.1, 0.55, 0.3), (0.95, 0.2, 0.25))
        cr.translate(x, ground)
        cr.scale(face, 1)
        hat = ("santa" if self.christmas else True) if ((self.halloween or self.christmas) and self.character != "image") else False
        if self.character == "robot":
            draw_robot(cr, H, t, st, self.color, self.rainbow, hat)
        elif self.character == "skeleton":
            draw_skeleton(cr, H, t, st, self.color if self.color != "#4080ff" else "", self.rainbow, hat)
        elif self.character == "image":
            draw_image(cr, H, t, st, self.image)
        else:
            draw_human(cr, H, t, st, self.color, self.rainbow, hat)
        cr.restore()
        if self.rainbow:  # sparkles all around
            cr.save()
            cr.translate(x, ground)
            ath._sparkles(cr, 0, -H * 0.5, H * 0.75, t, 0.8, color=(1, 1, 1), count=22, seed=9)
            cr.restore()
        if t >= T_BUBBLE and t < self.t_out + 0.2:
            self._draw_bubble(cr, t, w, h, H, ground, x)

    def _draw_bubble(self, cr, t, w, h, H, ground, x):
        px = H * 0.085
        maxw = min(w * 0.62, H * 2.6)
        lines, lh, tw = self._layout(cr, px, maxw)
        padx, pady = px * 0.8, px * 0.6
        bw, bh = tw + 2 * padx, len(lines) * lh * 1.12 + 2 * pady
        top_extra = H * (0.27 if ((self.halloween or self.christmas) and self.character != "image") else 0.05)
        bx = max(w * 0.015, min(w - bw - w * 0.015, x + H * 0.1))
        by = ground - H * 1.06 - top_extra - bh
        fill, border, tcol = self._bubble_colors()
        pop = _ease_back(max(0.0, min(1.0, (t - T_BUBBLE) / 0.35)))
        fade = 1.0 - max(0.0, min(1.0, (t - self.t_bow) / 0.45))
        tail_x, tail_y = max(bx + px, min(bx + bw - px, x + H * 0.03)), by + bh
        cr.save()
        cr.translate(tail_x, tail_y)
        cr.scale(pop, pop)
        cr.translate(-tail_x, -tail_y)
        cr.push_group()
        ath._rounded(cr, bx + 4, by + 8, bw, bh, px * 0.9)
        cr.set_source_rgba(0, 0, 0, 0.25)
        cr.fill()
        ath._rounded(cr, bx, by, bw, bh, px * 0.9)
        cr.move_to(tail_x - px * 0.7, by + bh - 2)
        cr.line_to(tail_x + px * 0.2, by + bh + px * 1.5)
        cr.line_to(tail_x + px * 0.9, by + bh - 2)
        cr.set_source_rgba(*fill)
        cr.fill_preserve()
        if self.rainbow:
            g = cairo.LinearGradient(bx, by, bx + bw, by)
            for i in range(7):
                g.add_color_stop_rgb(i / 6, *_hsv(i / 7 * 0.85 + t * 0.1, 0.8, 1))
            cr.set_source(g)
        else:
            cr.set_source_rgb(*border)
        cr.set_line_width(max(3, px * 0.12))
        cr.stroke()
        shown = int(max(0.0, t - T_TYPE) * TYPE_CPS)
        cursor = "▌" if (t - T_TYPE) % 0.8 < 0.45 and t < self.t_bow else ""
        layout = PangoCairo.create_layout(cr)
        fd = Pango.FontDescription("Sans Bold")
        fd.set_absolute_size(px * Pango.SCALE)
        layout.set_font_description(fd)
        left = shown
        cr.set_source_rgb(*tcol)
        for i, ln in enumerate(lines):  # reveal the text letter by letter, the cursor on the line being written
            typing_here = left <= len(ln)
            layout.set_text(ln[:max(0, left)] + (cursor if typing_here else ""), -1)
            cr.move_to(bx + padx, by + pady + i * lh * 1.12)
            PangoCairo.show_layout(cr, layout)
            left -= len(ln) + 1
            if typing_here:
                break
        cr.pop_group_to_source()
        cr.paint_with_alpha(fade)
        cr.restore()

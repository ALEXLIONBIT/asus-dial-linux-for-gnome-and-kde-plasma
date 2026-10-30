"""Shared by asus-dial (the driver) and asus-dial-manager (the settings app).

Holds the config file (~/.config/asus-dial/config.json), the list of built-in modes with their
icons and names in English / Spanish / Italian, and the key-name <-> Linux key-code tables used
by custom modes ("ctrl+shift+t", "p", "ctrl+c ctrl+v", ...).
"""
import json
import os
import re

import asus_dial_gpu as agpu

CONFIG_DIR = os.path.expanduser("~/.config/asus-dial")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
LANG_FILE = os.path.expanduser("~/.config/asus-dial.lang")
LANGS = ("en", "es", "it")
LANG_NAMES = {"en": "English", "es": "Español", "it": "Italiano"}

# Built-in modes. The position in these lists is the tool number used inside the driver.
BUILTIN_IDS = ["scroll", "volume", "brightness", "zoom", "video", "tabs", "arrows", "house", "power",
               "dice", "timer", "speed", "night", "windows", "find", "keylight", "language", "rick", "ai", "gpu", "suspend"]
ICONS = ["↕", "🔊", "☀", "🔍", "▶", "🗂", "↔", "🏠", "⏻", "🎲", "⏲", "⏩", "🌙", "🪟", "🔎", "⌨", "🌐", "✨", "🤖", "🎮", "😴"]
NAMES_L = {
    "en": ["Scroll", "Volume", "Brightness", "Zoom", "Video", "Tabs", "Arrows", "House", "Power off",
           "Dice", "Timer", "Speed", "Light", "Windows", "Find", "Keyboard", "Language", "Rickroll", "AI", "GPU", "Sleep"],
    "es": ["Desplazar", "Volumen", "Brillo", "Zoom", "Vídeo", "Pestañas", "Flechas", "Casa", "Apagar",
           "Dado", "Temporiz.", "Velocidad", "Luz", "Ventanas", "Buscar", "Teclado", "Idioma", "Rickroll", "IA", "GPU", "Sueño"],
    "it": ["Scorri", "Volume", "Luminosità", "Zoom", "Video", "Schede", "Frecce", "Casa", "Arresta",
           "Dado", "Timer", "Velocità", "Luce", "Finestre", "Trova", "Tastiera", "Lingua", "Rickroll", "AI", "GPU", "Sospendi"],
}
# default order of the radial menu
DEFAULT_ORDER = ["scroll", "volume", "brightness", "keylight", "night", "zoom", "video", "speed", "timer", "ai",
                 "tabs", "find", "windows", "arrows", "dice", "house", "rick", "language", "gpu", "suspend", "power"]
BROWSER_ONLY_IDS = ("tabs", "find")

# Look of the radial menu and of the on-screen messages (see asus_dial_theme.py for the drawing)
DEFAULT_THEME = {
    "bg_type": "color",        # color | image | rainbow | halloween | christmas | plasma
    "plasma_mode": "auto",     # plasma background: auto (follows the desktop's light/dark look) | light | dark
    "bg_color": "#141419",
    "bg_opacity": 0.88,        # 0..1
    "bg_image": "",            # cropped PNG written by the manager
    "image_dim": 0.35,         # 0..1, darkens the image so the text stays readable
    "blur": 0,                 # 0..40: frosted glass (blurs a snapshot of what is behind the menu)
    "accent": "#4080ff",       # selected slice and bars
    "text": "#ffffff",
    "glow": False,
    "glow_color": "#4080ff",
    "glow_strength": 0.8,      # 0..1
    "reflection": 0.0,         # 0..1: glossy highlight
    "shadow": False,
    "shadow_strength": 0.6,    # 0..1
    "sparkles": False,
    "speed": 0.5,              # animation speed of rainbow / sparkles / halloween / christmas
}
THEME_PRESETS = {
    "default": {},
    "glass": {"bg_type": "color", "bg_color": "#ffffff", "bg_opacity": 0.16, "blur": 18, "accent": "#7ab8ff", "text": "#ffffff",
              "reflection": 0.55, "shadow": True, "shadow_strength": 0.5, "glow": False, "sparkles": False},
    "neon": {"bg_type": "color", "bg_color": "#06060f", "bg_opacity": 0.92, "accent": "#ff2bd6", "text": "#e8fbff", "glow": True,
             "glow_color": "#ff2bd6", "glow_strength": 1.0, "reflection": 0.12, "shadow": True, "shadow_strength": 0.5, "sparkles": False},
    "rainbow": {"bg_type": "rainbow", "bg_opacity": 0.92, "accent": "#101018", "text": "#ffffff", "glow": True, "glow_color": "#ffffff",
                "glow_strength": 0.6, "reflection": 0.35, "shadow": True, "shadow_strength": 0.5, "sparkles": True},
    "sunset": {"bg_type": "color", "bg_color": "#2a0f2e", "bg_opacity": 0.92, "accent": "#ff7a45", "text": "#fff1e6", "glow": True,
               "glow_color": "#ff7a45", "glow_strength": 0.6, "reflection": 0.2, "shadow": True, "shadow_strength": 0.5, "sparkles": False},
    "paper": {"bg_type": "color", "bg_color": "#f4efe6", "bg_opacity": 0.96, "accent": "#3b82f6", "text": "#2b2b2b", "glow": False,
              "reflection": 0.3, "shadow": True, "shadow_strength": 0.45, "sparkles": False},
    "halloween": {"bg_type": "halloween", "bg_opacity": 0.95, "accent": "#ff7a00", "text": "#fff3e0", "glow": True, "glow_color": "#ff7a00",
                  "glow_strength": 0.9, "reflection": 0.0, "shadow": True, "shadow_strength": 0.6, "sparkles": False},
    "christmas": {"bg_type": "christmas", "bg_opacity": 0.95, "accent": "#d62828", "text": "#fff8e7", "glow": True, "glow_color": "#ffd166",
                  "glow_strength": 0.7, "reflection": 0.12, "shadow": True, "shadow_strength": 0.6, "sparkles": False, "speed": 0.5},
    "plasma": {"bg_type": "plasma", "plasma_mode": "auto", "bg_opacity": 0.6, "glow": False, "reflection": 0.0, "shadow": True,
               "shadow_strength": 0.45, "sparkles": False, "blur": 14},
    "oled": {"bg_type": "color", "bg_color": "#000000", "bg_opacity": 1.0, "accent": "#7c5cff", "text": "#ffffff", "glow": False,
             "reflection": 0.0, "shadow": False, "sparkles": False},
    "forest": {"bg_type": "color", "bg_color": "#0a1c11", "bg_opacity": 0.94, "accent": "#2f9e5e", "text": "#e6f6ea", "glow": True,
               "glow_color": "#3ddc84", "glow_strength": 0.45, "reflection": 0.14, "shadow": True, "shadow_strength": 0.55, "sparkles": True, "speed": 0.3},
    "midnight": {"bg_type": "color", "bg_color": "#060a22", "bg_opacity": 0.94, "accent": "#4f6bff", "text": "#e6ebff", "glow": True,
                 "glow_color": "#5b7bff", "glow_strength": 0.55, "reflection": 0.18, "shadow": True, "shadow_strength": 0.55, "sparkles": True, "speed": 0.35},
    "ocean": {"bg_type": "color", "bg_color": "#05202c", "bg_opacity": 0.93, "accent": "#13a6b5", "text": "#e0fbff", "glow": True,
              "glow_color": "#22d3ee", "glow_strength": 0.5, "reflection": 0.22, "shadow": True, "shadow_strength": 0.5, "sparkles": False},
    "sakura": {"bg_type": "color", "bg_color": "#2a1120", "bg_opacity": 0.93, "accent": "#ec5fa3", "text": "#ffeaf4", "glow": True,
               "glow_color": "#f9a8d4", "glow_strength": 0.5, "reflection": 0.2, "shadow": True, "shadow_strength": 0.5, "sparkles": True, "speed": 0.3},
    "ember": {"bg_type": "color", "bg_color": "#190705", "bg_opacity": 0.94, "accent": "#ff5a1f", "text": "#fff0e6", "glow": True,
              "glow_color": "#ff7a1a", "glow_strength": 0.75, "reflection": 0.1, "shadow": True, "shadow_strength": 0.6, "sparkles": False},
}
PRESET_NAMES = {
    "default": ("Default", "Predeterminado", "Predefinito"), "glass": ("Glass", "Cristal", "Vetro"),
    "neon": ("Neon", "Neón", "Neon"), "rainbow": ("Rainbow ✨", "Arcoíris ✨", "Arcobaleno ✨"),
    "sunset": ("Sunset", "Atardecer", "Tramonto"), "paper": ("Paper (light)", "Papel (claro)", "Carta (chiaro)"),
    "halloween": ("Halloween 🎃", "Halloween 🎃", "Halloween 🎃"),
    "christmas": ("Christmas 🎄", "Navidad 🎄", "Natale 🎄"), "plasma": ("Plasma 💠", "Plasma 💠", "Plasma 💠"), "oled": ("OLED black", "Negro OLED", "Nero OLED"),
    "forest": ("Forest 🌲", "Bosque 🌲", "Foresta 🌲"), "midnight": ("Midnight 🌙", "Medianoche 🌙", "Mezzanotte 🌙"),
    "ocean": ("Ocean 🌊", "Océano 🌊", "Oceano 🌊"), "sakura": ("Sakura 🌸", "Sakura 🌸", "Sakura 🌸"), "ember": ("Ember 🔥", "Brasa 🔥", "Brace 🔥"),
}


def theme_of(cfg):
    """The theme dict with every key present (and values of the right kind)."""
    th = dict(DEFAULT_THEME)
    user = cfg.get("theme") if isinstance(cfg.get("theme"), dict) else {}
    for k, v in user.items():
        if k in th and isinstance(v, type(th[k])) or (k in th and isinstance(th[k], float) and isinstance(v, int) and not isinstance(v, bool)):
            th[k] = v
    return th


# Animations of the menu / messages (driver) and of the settings app
ANIM_TYPES = ("none", "fade", "zoom", "slide", "bounce", "spin", "fan")
ANIM_EASES = ("smooth", "linear", "back", "elastic", "bounce")
APP_TRANSITIONS = ("none", "crossfade", "slide", "slide-up", "over", "under")
DEFAULT_ANIMATION = {
    "in_type": "zoom", "in_ms": 220,        # how the menu appears
    "out_type": "fade", "out_ms": 160,      # how it goes away (0 ms or "none" = at once)
    "ease": "smooth",                       # motion curve
    "highlight": True, "highlight_ms": 120, # the selected slice slides from one slice to the next
    "app": True, "app_type": "crossfade", "app_ms": 250,  # settings app: tab change and window fade-in
}


def animation_of(cfg):
    """The animation settings with every key present and valid."""
    an = dict(DEFAULT_ANIMATION)
    user = cfg.get("animation") if isinstance(cfg.get("animation"), dict) else {}
    for k, v in user.items():
        if k in an and (isinstance(v, type(an[k])) and not (isinstance(an[k], int) and isinstance(v, bool)) or
                        (isinstance(an[k], bool) and isinstance(v, bool))):
            an[k] = v
    if an["in_type"] not in ANIM_TYPES:
        an["in_type"] = DEFAULT_ANIMATION["in_type"]
    if an["out_type"] not in ANIM_TYPES:
        an["out_type"] = DEFAULT_ANIMATION["out_type"]
    if an["ease"] not in ANIM_EASES:
        an["ease"] = "smooth"
    if an["app_type"] not in APP_TRANSITIONS:
        an["app_type"] = "crossfade"
    for k in ("in_ms", "out_ms", "highlight_ms", "app_ms"):
        an[k] = max(0, min(800, int(an[k])))
    return an


SENSITIVITY_DEFAULT, SENSITIVITY_MIN, SENSITIVITY_MAX = 2.5, 0.5, 6.0  # how many times faster than the original 1.0 the dial reacts


def sensitivity(cfg):
    """Dial sensitivity from the config, kept in range: 2 means half the turning is needed for each step."""
    try:
        return max(SENSITIVITY_MIN, min(SENSITIVITY_MAX, float(cfg.get("sensitivity", SENSITIVITY_DEFAULT))))
    except (TypeError, ValueError):
        return SENSITIVITY_DEFAULT


DEFAULT_CONFIG = {
    "version": 1,
    "sensitivity": SENSITIVITY_DEFAULT,
    "modes": {"disabled": [], "order": list(DEFAULT_ORDER)},
    "custom": [],  # {"id": "p", "name": "P", "icon": "⌨", "click": "p", "cw": "", "ccw": ""}
    "welcome": {"enabled": True, "character": "human", "color": "#4080ff", "rainbow": False, "image": "", "message": "", "name": ""},
    "theme": {},
    "animation": {},
}


# ------------------------------------------------------------------ config file
def _merge(default, data):
    out = json.loads(json.dumps(default))
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = _merge(out[k], v)
            else:
                out[k] = v
    return out


def load():
    """The config, with defaults filled in. A missing or broken file gives the defaults."""
    try:
        with open(CONFIG_FILE) as f:
            cfg = _merge(DEFAULT_CONFIG, json.load(f))
    except (OSError, ValueError):
        cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    custom = []
    for c in cfg.get("custom", []):
        if isinstance(c, dict) and c.get("id") and c.get("name"):
            custom.append({"id": str(c["id"]), "name": str(c["name"]), "icon": str(c.get("icon") or "⌨"),
                           "click": str(c.get("click") or ""), "cw": str(c.get("cw") or ""), "ccw": str(c.get("ccw") or "")})
    cfg["custom"] = custom
    return cfg


def save(cfg):
    """Write the config atomically (the driver notices the change by itself)."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_FILE)


def config_mtime():
    try:
        return os.stat(CONFIG_FILE).st_mtime_ns
    except OSError:
        return 0


def mode_order(cfg):
    """Ids of the enabled modes, in menu order: built-ins by id, custom ones as 'custom:<id>'."""
    known = [i for i in BUILTIN_IDS if i != "gpu" or agpu.has_choice()]  # the GPU mode exists only with 2+ graphics cards
    known += ["custom:" + c["id"] for c in cfg["custom"]]
    order = [i for i in cfg["modes"].get("order", []) if i in known]
    order += [i for i in DEFAULT_ORDER if i in known and i not in order]
    order += [i for i in known if i not in order]
    disabled = set(cfg["modes"].get("disabled", []))
    return [i for i in order if i not in disabled]


def all_modes(cfg):
    """Every mode (enabled or not) in menu order, as (id, enabled)."""
    disabled = set(cfg["modes"].get("disabled", []))
    cfg2 = json.loads(json.dumps(cfg))
    cfg2["modes"]["disabled"] = []
    return [(i, i not in disabled) for i in mode_order(cfg2)]


def slug(name, taken):
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "mode"
    n, cand = 1, base
    while cand in taken:
        n += 1
        cand = f"{base}-{n}"
    return cand


# ------------------------------------------------------------------ keys
# Linux input event codes. They are physical key positions (US layout names).
_LETTERS = dict(zip("abcdefghijklmnopqrstuvwxyz",
                    [30, 48, 46, 32, 18, 33, 34, 35, 23, 36, 37, 38, 50, 49, 24, 25, 16, 19, 31, 20, 22, 47, 17, 45, 21, 44]))
KEY_NAMES = dict(_LETTERS)
KEY_NAMES.update({str(d): c for d, c in zip(range(1, 10), range(2, 11))})
KEY_NAMES["0"] = 11
KEY_NAMES.update({
    "minus": 12, "equal": 13, "backspace": 14, "tab": 15, "bracketleft": 26, "bracketright": 27, "enter": 28,
    "semicolon": 39, "apostrophe": 40, "grave": 41, "backslash": 43, "comma": 51, "period": 52, "slash": 53,
    "space": 57, "esc": 1, "capslock": 58, "home": 102, "up": 103, "pageup": 104, "left": 105, "right": 106,
    "end": 107, "down": 108, "pagedown": 109, "insert": 110, "delete": 111, "print": 99, "pause": 119, "menu": 127,
    "kpplus": 78, "kpminus": 74, "kpasterisk": 55, "kpslash": 98, "kpenter": 96,
    "volumeup": 115, "volumedown": 114, "mute": 113, "playpause": 164, "next": 163, "previous": 165,
})
KEY_NAMES.update({f"f{i}": c for i, c in zip(range(1, 11), range(59, 69))})
KEY_NAMES.update({"f11": 87, "f12": 88})
MOD_NAMES = {"ctrl": 29, "shift": 42, "alt": 56, "super": 125, "altgr": 100}
_ALIASES = {"control": "ctrl", "ctl": "ctrl", "win": "super", "meta": "super", "windows": "super", "return": "enter",
            "escape": "esc", "del": "delete", "pgup": "pageup", "pgdn": "pagedown", "ins": "insert", "plus": "kpplus",
            "spacebar": "space", "bksp": "backspace", "arrowup": "up", "arrowdown": "down", "arrowleft": "left",
            "arrowright": "right"}
CODE_NAMES = {c: n for n, c in KEY_NAMES.items()}
CODE_NAMES.update({c: n for n, c in MOD_NAMES.items()})
ALL_KEYCODES = sorted(set(KEY_NAMES.values()) | set(MOD_NAMES.values()))


def parse_combo(text):
    """'ctrl+shift+t' -> ([29, 42], 20). A lone modifier ('super') is a key press of that modifier."""
    parts = [_ALIASES.get(p, p) for p in re.split(r"\s*\+\s*", text.strip().lower()) if p]
    if not parts:
        raise ValueError("empty")
    *mods, key = parts
    codes = []
    for m in mods:
        if m not in MOD_NAMES:
            raise ValueError(f"unknown modifier: {m}")
        codes.append(MOD_NAMES[m])
    if key in MOD_NAMES and not mods:
        return [], MOD_NAMES[key]
    if key not in KEY_NAMES:
        raise ValueError(f"unknown key: {key}")
    return codes, KEY_NAMES[key]


def parse_sequence(text):
    """'ctrl+c ctrl+v' -> [([29], 46), ([29], 47)]. Combos are separated by spaces or commas. Empty = []."""
    return [parse_combo(tok) for tok in re.split(r"[\s,]+", text.strip()) if tok]


def combo_text(mod_codes, key_code):
    return "+".join([CODE_NAMES[m] for m in mod_codes] + [CODE_NAMES.get(key_code, f"key{key_code}")])

"""What the dial asks of the desktop, for GNOME and KDE Plasma: screen and keyboard brightness, night light, screen
zoom, and which window has the focus.

Everything else the dial does (keys, scrolling, volume, media, timer, GPU, lock) goes through uinput, PipeWire, MPRIS,
logind and environment.d, and works the same on both. `for_session(bus)` returns the backend of the running session:

  * GNOME: gsettings (night light, magnifier), Mutter / gnome-settings-daemon (brightness), xprop for the focus.
  * KDE Plasma: KWin (night light through kwinrc, the Zoom effect, a small KWin script that reports the active window
    over D-Bus, so it works on Wayland too) and PowerDevil (brightness, keyboard backlight).

Both fall back to UPower for the keyboard backlight, so it also works where the desktop has no such control.
"""
import json
import math
import os
import shutil
import subprocess

from gi.repository import Gio, GLib

DBUS_NAME = "io.github.alexlionbit.AsusDial"  # owned by the dial on KDE: the KWin script reports the focus to it
DBUS_PATH = "/io/github/alexlionbit/AsusDial"
KWIN_SCRIPT_NAME = "asus-dial-focus"
KWIN_SCRIPT_FILE = os.path.expanduser("~/.local/share/asus-dial/kwin-focus.js")
KWIN_SCRIPT = """// Written by asus-dial: tells the dial which window has the focus (and its title), on X11 and Wayland alike.
var watched = null;
function report() {
    var w = workspace.activeWindow;
    callDBus("%(name)s", "%(path)s", "%(name)s", "WindowActivated",
             w ? String(w.resourceClass || "") : "", w ? String(w.caption || "") : "");
}
function follow(w) {
    if (watched) {
        try { watched.captionChanged.disconnect(report); } catch (e) {}
    }
    watched = w;
    if (w) {
        w.captionChanged.connect(report);
    }
    report();
}
workspace.windowActivated.connect(follow);
follow(workspace.activeWindow);
""" % {"name": DBUS_NAME, "path": DBUS_PATH}
DBUS_XML = f"""<node><interface name="{DBUS_NAME}">
  <method name="WindowActivated"><arg type="s" name="resource_class" direction="in"/><arg type="s" name="caption" direction="in"/></method>
</interface></node>"""


def overlay_env():
    """Variables a program that draws on-screen overlays (the dial's menu and messages, the welcome) sets before GTK starts.

    Overlays run on X11: Wayland lets no app place its window or keep it above the others. GNOME scales X11 windows by
    itself; Plasma lets them draw at the screen's real resolution and tells the scale only through Xft.dpi, which GTK 3
    does not use for its windows, so there GDK_SCALE (a whole number) makes the overlays as big as on GNOME."""
    if "kde" not in os.environ.get("XDG_CURRENT_DESKTOP", "").lower():
        return {}
    env = {"GDK_BACKEND": "x11"}
    if not os.environ.get("GDK_SCALE"):
        try:
            out = subprocess.run(["xrdb", "-query"], capture_output=True, text=True, timeout=2).stdout
            dpi = next(float(line.split()[1]) for line in out.splitlines() if line.startswith("Xft.dpi:"))
        except (OSError, subprocess.SubprocessError, StopIteration, IndexError, ValueError):
            dpi = 96.0
        if round(dpi / 96) > 1:
            env["GDK_SCALE"] = str(round(dpi / 96))
    return env


def _has_owner(bus, name):
    try:
        return bus.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "NameHasOwner",
                             GLib.Variant("(s)", (name,)), GLib.VariantType("(b)"), Gio.DBusCallFlags.NONE, 500, None).unpack()[0]
    except GLib.Error:
        return False


def for_session(bus):
    """The backend of the running desktop: asked to D-Bus first (it cannot be stale), then to XDG_CURRENT_DESKTOP."""
    if _has_owner(bus, "org.kde.KWin"):
        return KdeDesktop(bus)
    if _has_owner(bus, "org.gnome.Shell"):
        return GnomeDesktop(bus)
    current = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    return KdeDesktop(bus) if "kde" in current else GnomeDesktop(bus)


class Desktop:
    """What both desktops share. Brightness is 0-100; the keyboard backlight is a fraction 0..1 (None = no control)."""
    name = "desktop"

    def __init__(self, bus):
        self.bus = bus
        self._system = None

    def call(self, name, path, iface, method, args=None, reply=None, bus=None):
        r = (bus or self.bus).call_sync(name, path, iface, method, args, GLib.VariantType(reply) if reply else None,
                                        Gio.DBusCallFlags.NONE, 500, None)
        return r.unpack() if r is not None else ()

    def prop(self, name, path, iface, prop, bus=None):
        return self.call(name, path, "org.freedesktop.DBus.Properties", "Get", GLib.Variant("(ss)", (iface, prop)), "(v)", bus)[0]

    # --- keyboard backlight: UPower, the desktop-independent way ---
    def system_bus(self):
        if self._system is None:
            self._system = Gio.bus_get_sync(Gio.BusType.SYSTEM)
        return self._system

    def _upower_kbd(self, method, args=None):
        return self.call("org.freedesktop.UPower", "/org/freedesktop/UPower/KbdBacklight", "org.freedesktop.UPower.KbdBacklight",
                         method, args, None, self.system_bus())

    def get_keylight(self):
        try:
            top = self._upower_kbd("GetMaxBrightness")[0]
            return self._upower_kbd("GetBrightness")[0] / top if top > 0 else None
        except GLib.Error:
            return None

    def set_keylight(self, fraction):
        try:
            top = self._upower_kbd("GetMaxBrightness")[0]
            self._upower_kbd("SetBrightness", GLib.Variant("(i)", (round(fraction * top),)))
            return True
        except GLib.Error:
            return False

    # --- focused window: X11 windows tell their class and title through xprop ---
    @staticmethod
    def _x_active(prop):
        try:
            root = subprocess.run(["xprop", "-root", "_NET_ACTIVE_WINDOW"], capture_output=True, text=True, timeout=0.5).stdout
            wid = root.split()[-1]
            if not wid.startswith("0x") or int(wid, 16) == 0:
                return None
            out = subprocess.run(["xprop", "-id", wid, prop], capture_output=True, text=True, timeout=0.5).stdout
        except (OSError, IndexError, ValueError, subprocess.SubprocessError):
            return None
        return out if "=" in out else None  # "not found" = a window that is gone or has no such property

    def focus_class(self):
        """WM class (lower case) of the focused window, or None if the desktop cannot tell."""
        cls = self._x_active("WM_CLASS")
        return cls.lower() if cls is not None else None

    def active_title(self):
        return self._x_active("_NET_WM_NAME") or ""


class GnomeDesktop(Desktop):
    name = "gnome"

    def __init__(self, bus):
        super().__init__(bus)
        self.color = self._settings("org.gnome.settings-daemon.plugins.color")
        self.mag_apps = self._settings("org.gnome.desktop.a11y.applications")
        self.mag = self._settings("org.gnome.desktop.a11y.magnifier")

    @staticmethod
    def _settings(schema):
        src = Gio.SettingsSchemaSource.get_default()
        return Gio.Settings.new(schema) if src and src.lookup(schema, True) else None

    def _power(self, method, args):
        return self.bus.call_sync("org.gnome.SettingsDaemon.Power", "/org/gnome/SettingsDaemon/Power",
                                  "org.freedesktop.DBus.Properties", method, args,
                                  None, Gio.DBusCallFlags.NONE, 500, None)

    # Screen brightness. GNOME 48+ moved it into Mutter (DisplayConfig.Backlight, in the panel's own units);
    # older GNOME has it in gnome-settings-daemon (a plain 0-100 property). Both are tried, Mutter first.
    def _backlight(self):
        """(serial, [outputs with a backlight]) from Mutter, or None if this GNOME has no such property."""
        try:
            serial, outs = self.prop("org.gnome.Mutter.DisplayConfig", "/org/gnome/Mutter/DisplayConfig", "org.gnome.Mutter.DisplayConfig", "Backlight")
            outs = [o for o in outs if o.get("active", True) and o["max"] > o["min"]]
            return (serial, outs) if outs else None
        except (GLib.Error, KeyError, ValueError):
            return None

    def get_brightness(self):
        bl = self._backlight()
        if bl:
            o = bl[1][0]
            return round((o["value"] - o["min"]) * 100 / (o["max"] - o["min"]))
        try:
            return self._power("Get", GLib.Variant("(ss)", ("org.gnome.SettingsDaemon.Power.Screen", "Brightness"))).unpack()[0]
        except GLib.Error:
            return None

    def set_brightness(self, pct):
        bl = self._backlight()
        if bl:
            serial, outs = bl
            for o in outs:
                value = round(o["min"] + pct * (o["max"] - o["min"]) / 100)
                try:
                    self.call("org.gnome.Mutter.DisplayConfig", "/org/gnome/Mutter/DisplayConfig", "org.gnome.Mutter.DisplayConfig",
                              "SetBacklight", GLib.Variant("(usi)", (serial, o["connector"], value)))
                except GLib.Error:
                    pass
            return
        try:
            self._power("Set", GLib.Variant("(ssv)", ("org.gnome.SettingsDaemon.Power.Screen", "Brightness", GLib.Variant("i", pct))))
        except GLib.Error:
            pass

    def get_keylight(self):
        try:
            pct = self._power("Get", GLib.Variant("(ss)", ("org.gnome.SettingsDaemon.Power.Keyboard", "Brightness"))).unpack()[0]
            return max(0, pct) / 100
        except GLib.Error:
            return super().get_keylight()

    def set_keylight(self, fraction):
        try:
            self._power("Set", GLib.Variant("(ssv)", ("org.gnome.SettingsDaemon.Power.Keyboard", "Brightness", GLib.Variant("i", round(fraction * 100)))))
            return True
        except GLib.Error:
            return super().set_keylight(fraction)

    # --- night light: gnome-settings-daemon's color plugin ---
    def night_available(self):
        return self.color is not None

    def night_temperature(self):
        return self.color.get_uint("night-light-temperature")

    def set_night_temperature(self, k):
        self.color.set_uint("night-light-temperature", k)
        Gio.Settings.sync()

    def night_save(self):
        c = self.color
        return {"desktop": self.name, "enabled": c.get_boolean("night-light-enabled"), "automatic": c.get_boolean("night-light-schedule-automatic"),
                "from": c.get_double("night-light-schedule-from"), "to": c.get_double("night-light-schedule-to")}

    def night_force_on(self):
        """On all day long, whatever the user's schedule (night_save keeps that schedule)."""
        c = self.color
        c.set_boolean("night-light-schedule-automatic", False)
        c.set_double("night-light-schedule-from", 0.0)
        c.set_double("night-light-schedule-to", 24.0)
        c.set_boolean("night-light-enabled", True)
        Gio.Settings.sync()

    def night_restore(self, saved):
        if not saved or saved.get("desktop", self.name) != self.name:
            saved = {"enabled": False, "automatic": True, "from": 20.0, "to": 6.0}
        c = self.color
        c.set_double("night-light-schedule-from", saved["from"])
        c.set_double("night-light-schedule-to", saved["to"])
        c.set_boolean("night-light-schedule-automatic", saved["automatic"])
        c.set_boolean("night-light-enabled", saved["enabled"])
        Gio.Settings.sync()

    # --- screen zoom: GNOME's magnifier ---
    def get_magnifier(self):
        if not (self.mag and self.mag_apps) or not self.mag_apps.get_boolean("screen-magnifier-enabled"):
            return 1.0
        return self.mag.get_double("mag-factor")

    def set_magnifier(self, factor, step, top):
        """Zoom the screen by `factor` (rounded to `step`, at most `top`); returns the factor really used."""
        if not (self.mag and self.mag_apps):
            return 1.0
        factor = max(1.0, min(top, round(factor / step) * step))
        if factor <= 1.0:
            self.mag_apps.set_boolean("screen-magnifier-enabled", False)
            self.mag.set_double("mag-factor", 1.0)
        else:
            self.mag.set_double("mag-factor", factor)
            self.mag_apps.set_boolean("screen-magnifier-enabled", True)
        Gio.Settings.sync()
        return factor

    # Native Wayland windows: GNOME does not tell anybody which one has the focus, so focus_class stays the xprop one.


class KdeDesktop(Desktop):
    name = "kde"
    NIGHT_GROUP = "NightColor"  # the kwinrc group of the night light (its old name, still the one KWin reads)
    NIGHT_DEFAULT_K = 4500

    def __init__(self, bus):
        super().__init__(bus)
        self.focus = None  # (resource class, caption) told by the KWin script; None until it has spoken
        self.zoom_steps = 0  # KWin's zoom has no "get": the dial counts its own steps from 1×
        self._serve_focus()

    # --- the KWin script that reports the focused window ---
    def _serve_focus(self):
        try:
            info = Gio.DBusNodeInfo.new_for_xml(DBUS_XML)
            self.bus.register_object(DBUS_PATH, info.interfaces[0], self._on_call, None, None)
        except GLib.Error:
            return
        Gio.bus_own_name_on_connection(self.bus, DBUS_NAME, Gio.BusNameOwnerFlags.REPLACE, lambda *_: self._load_script(), None)

    def _on_call(self, _conn, _sender, _path, _iface, method, params, invocation):
        if method == "WindowActivated":
            cls, caption = params.unpack()
            self.focus = (cls.lower(), caption)
        invocation.return_value(None)

    def _scripting(self, method, args=None, reply=None):
        return self.call("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", method, args, reply)

    def _load_script(self):
        """(Re)load the focus script, so it reports to this dial process right away."""
        try:
            os.makedirs(os.path.dirname(KWIN_SCRIPT_FILE), exist_ok=True)
            with open(KWIN_SCRIPT_FILE, "w") as f:
                f.write(KWIN_SCRIPT)
            if self._scripting("isScriptLoaded", GLib.Variant("(s)", (KWIN_SCRIPT_NAME,)), "(b)")[0]:
                self._scripting("unloadScript", GLib.Variant("(s)", (KWIN_SCRIPT_NAME,)), "(b)")
            sid = self._scripting("loadScript", GLib.Variant("(ss)", (KWIN_SCRIPT_FILE, KWIN_SCRIPT_NAME)), "(i)")[0]
            if sid >= 0:
                self.call("org.kde.KWin", f"/Scripting/Script{sid}", "org.kde.kwin.Script", "run")
        except (GLib.Error, OSError) as e:
            print(f"asus-dial: no KWin focus script ({e})", flush=True)

    def focus_class(self):
        if self.focus is not None:
            return self.focus[0]
        return super().focus_class()

    def active_title(self):
        if self.focus is not None:
            return self.focus[1]
        return super().active_title()

    # --- screen brightness: PowerDevil (Plasma 6.1+ per display, older Plasma one value) ---
    def _display(self):
        """D-Bus path of the display whose brightness the dial drives (the built-in panel first), or None."""
        try:
            names = self.prop("org.kde.ScreenBrightness", "/org/kde/ScreenBrightness", "org.kde.ScreenBrightness", "DisplaysDBusNames")
        except GLib.Error:
            return None
        paths = [f"/org/kde/ScreenBrightness/{n}" for n in names]
        for p in paths:
            try:
                if self.prop("org.kde.ScreenBrightness", p, "org.kde.ScreenBrightness.Display", "IsInternal"):
                    return p
            except GLib.Error:
                pass
        return paths[0] if paths else None

    def get_brightness(self):
        p = self._display()
        try:
            if p:
                get = lambda key: self.prop("org.kde.ScreenBrightness", p, "org.kde.ScreenBrightness.Display", key)
                top = get("MaxBrightness")
                return round(get("Brightness") * 100 / top) if top > 0 else None
            bc = ("org.kde.Solid.PowerManagement", "/org/kde/Solid/PowerManagement/Actions/BrightnessControl",
                  "org.kde.Solid.PowerManagement.Actions.BrightnessControl")
            top = self.call(*bc, "brightnessMax", None, "(i)")[0]
            return round(self.call(*bc, "brightness", None, "(i)")[0] * 100 / top) if top > 0 else None
        except GLib.Error:
            return None

    def set_brightness(self, pct):
        p = self._display()
        try:
            if p:
                top = self.prop("org.kde.ScreenBrightness", p, "org.kde.ScreenBrightness.Display", "MaxBrightness")
                # flag 1 = no Plasma OSD: the dial shows its own
                self.call("org.kde.ScreenBrightness", p, "org.kde.ScreenBrightness.Display", "SetBrightness",
                          GLib.Variant("(iu)", (round(pct * top / 100), 1)))
                return
            bc = ("org.kde.Solid.PowerManagement", "/org/kde/Solid/PowerManagement/Actions/BrightnessControl",
                  "org.kde.Solid.PowerManagement.Actions.BrightnessControl")
            top = self.call(*bc, "brightnessMax", None, "(i)")[0]
            self.call(*bc, "setBrightnessSilent", GLib.Variant("(i)", (round(pct * top / 100),)))
        except GLib.Error:
            pass

    # --- keyboard backlight: PowerDevil, else UPower ---
    KBD = ("org.kde.Solid.PowerManagement", "/org/kde/Solid/PowerManagement/Actions/KeyboardBrightnessControl",
           "org.kde.Solid.PowerManagement.Actions.KeyboardBrightnessControl")

    def get_keylight(self):
        try:
            top = self.call(*self.KBD, "keyboardBrightnessMax", None, "(i)")[0]
            if top > 0:
                return self.call(*self.KBD, "keyboardBrightness", None, "(i)")[0] / top
        except GLib.Error:
            pass
        return super().get_keylight()

    def set_keylight(self, fraction):
        try:
            top = self.call(*self.KBD, "keyboardBrightnessMax", None, "(i)")[0]
            if top > 0:
                self.call(*self.KBD, "setKeyboardBrightnessSilent", GLib.Variant("(i)", (round(fraction * top),)))
                return True
        except GLib.Error:
            pass
        return super().set_keylight(fraction)

    # --- night light: KWin reads kwinrc again as soon as it changes (--notify) ---
    def _night_read(self, key, default):
        try:
            out = subprocess.run(["kreadconfig6", "--file", "kwinrc", "--group", self.NIGHT_GROUP, "--key", key, "--default", str(default)],
                                 capture_output=True, text=True, timeout=3).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return str(default)
        return out or str(default)

    def _night_write(self, **values):
        for key, value in values.items():
            if value is None:
                cmd = ["kwriteconfig6", "--file", "kwinrc", "--group", self.NIGHT_GROUP, "--key", key, "--notify", "--delete"]
            else:
                value = str(value).lower() if isinstance(value, bool) else str(value)
                cmd = ["kwriteconfig6", "--file", "kwinrc", "--group", self.NIGHT_GROUP, "--key", key, "--notify", value]
            subprocess.run(cmd, capture_output=True, timeout=3)

    def night_available(self):
        if not shutil.which("kwriteconfig6"):
            return False
        try:
            return bool(self.prop("org.kde.KWin.NightLight", "/org/kde/KWin/NightLight", "org.kde.KWin.NightLight", "available"))
        except GLib.Error:
            return False

    def night_temperature(self):
        try:
            return int(self._night_read("NightTemperature", self.NIGHT_DEFAULT_K))
        except ValueError:
            return self.NIGHT_DEFAULT_K

    def set_night_temperature(self, k):
        self._night_write(NightTemperature=k)

    def night_save(self):
        # None = the key was not in kwinrc (KWin's default): restoring deletes it again
        raw = lambda key: self._night_read(key, "") or None
        return {"desktop": self.name, "Active": raw("Active"), "Mode": raw("Mode")}

    def night_force_on(self):
        self._night_write(Active=True, Mode="Constant")

    def night_restore(self, saved):
        if not saved or saved.get("desktop") != self.name:
            saved = {"Active": None, "Mode": None}
        self._night_write(Active=saved.get("Active"), Mode=saved.get("Mode"))

    # --- screen zoom: KWin's Zoom effect, driven through its global shortcuts ---
    def _zoom_factor(self):
        try:
            out = subprocess.run(["kreadconfig6", "--file", "kwinrc", "--group", "Effect-zoom", "--key", "ZoomFactor", "--default", "1.2"],
                                 capture_output=True, text=True, timeout=3).stdout.strip()
            return max(1.05, float(out))
        except (OSError, subprocess.SubprocessError, ValueError):
            return 1.2

    def _zoom(self, action):
        self.call("org.kde.kglobalaccel", "/component/kwin", "org.kde.kglobalaccel.Component", "invokeShortcut",
                  GLib.Variant("(s)", (action,)))

    def get_magnifier(self):
        return round(self._zoom_factor() ** self.zoom_steps, 2)

    def set_magnifier(self, factor, step, top):
        """KWin zooms by its own factor per step (1.2× by default): the nearest number of steps to `factor`, at least one
        step in the asked direction, at most `top`."""
        zf, now = self._zoom_factor(), self.zoom_steps
        want = 0 if factor <= 1.0 else round(math.log(min(top, factor)) / math.log(zf))
        if factor > zf ** now and want <= now and zf ** (now + 1) <= top:
            want = now + 1
        elif factor < zf ** now and want >= now:
            want = max(0, now - 1)
        try:
            if want == 0:
                self._zoom("view_actual_size")
            else:
                for _ in range(abs(want - now)):
                    self._zoom("view_zoom_in" if want > now else "view_zoom_out")
            self.zoom_steps = want
        except GLib.Error:
            pass
        return self.get_magnifier()


if __name__ == "__main__":  # a quick look at what this session offers: python3 asus_dial_desktop.py
    d = for_session(Gio.bus_get_sync(Gio.BusType.SESSION))
    print(json.dumps({"desktop": d.name, "brightness": d.get_brightness(), "keyboard": d.get_keylight(),
                      "night_light": d.night_available() and d.night_temperature(), "zoom": d.get_magnifier(),
                      "focus": d.focus_class()}, indent=1))

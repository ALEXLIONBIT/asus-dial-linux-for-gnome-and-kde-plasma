"""GPU detection and choice, shared by asus-dial (the GPU mode), asus-dial-manager and the asus-dial-gpu command.

On a laptop with two or more graphics cards the desktop is drawn by one of them (the default one) and the other can be
asked to render an app (the "PRIME render offload" of the drivers). Choosing a GPU here means: the apps you start
render on that card. It is done the way GNOME's "Launch using Discrete Graphics Card" (Plasma's "Run using dedicated
graphics card") does it, with environment variables, and it needs no root:

  * ~/.config/environment.d/60-asus-dial-gpu.conf holds them for every future login (the whole session, the GNOME Shell or
    Plasma launcher included, starts with them);
  * `systemctl --user set-environment` gives them at once to everything the session starts from now on (services,
    D-Bus activated apps). Programs already running keep the GPU they were started on.

Choosing the default GPU removes the variables again. `asus-dial-gpu run <command>` starts one command on the chosen GPU
right away, whatever the session was started with.
"""
import glob
import os
import shlex
import shutil
import subprocess
import time

ENV_FILE = os.path.expanduser("~/.config/environment.d/60-asus-dial-gpu.conf")
STATE_FILE = os.path.expanduser("~/.config/asus-dial.gpu")  # id of the chosen GPU, e.g. pci-0000_01_00_0
NVIDIA, AMD, INTEL = 0x10DE, 0x1002, 0x8086
GPU_VARS = ("DRI_PRIME", "__NV_PRIME_RENDER_OFFLOAD", "__GLX_VENDOR_LIBRARY_NAME", "__VK_LAYER_NV_optimus", "VK_LOADER_DRIVERS_SELECT")
_cache = {"t": 0.0, "gpus": []}


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def _short_name(slot, vendor):
    """'GA106M [GeForce RTX 3060 Mobile / Max-Q]' -> 'GeForce RTX 3060 Mobile'; falls back to the vendor name."""
    fallback = {NVIDIA: "NVIDIA GPU", AMD: "AMD GPU", INTEL: "Intel GPU"}.get(vendor, "GPU")
    if not shutil.which("lspci"):
        return fallback
    try:
        out = subprocess.run(["lspci", "-s", slot.split(":", 1)[1], "-mm"], capture_output=True, text=True, timeout=3).stdout
        fields = shlex.split(out.splitlines()[0])
        dev = fields[3]
    except (OSError, subprocess.SubprocessError, IndexError, ValueError):
        return fallback
    if "[" in dev and "]" in dev:
        dev = dev[dev.index("[") + 1:dev.rindex("]")]
    return dev.split(" / ")[0].strip() or fallback


def _env_for(vendor, pci_id, default):
    """The variables that make an app render on this card (none for the default one)."""
    if default:
        return {}
    if vendor == NVIDIA:
        return {"__NV_PRIME_RENDER_OFFLOAD": "1", "__GLX_VENDOR_LIBRARY_NAME": "nvidia", "__VK_LAYER_NV_optimus": "NVIDIA_only",
                "VK_LOADER_DRIVERS_SELECT": "*nvidia*"}
    return {"DRI_PRIME": pci_id}


def gpus(refresh=False):
    """The graphics cards of the PC: [{"id", "name", "integrated", "default", "env"}], the default one first."""
    if not refresh and time.monotonic() - _cache["t"] < 30 and _cache["t"]:
        return _cache["gpus"]
    found = []
    for card in sorted(glob.glob("/sys/class/drm/card[0-9]*")):
        if not card[len("/sys/class/drm/card"):].isdigit():  # skip card0-HDMI-A-1 and friends
            continue
        dev = os.path.join(card, "device")
        if not _read(os.path.join(dev, "class")).startswith("0x03"):  # display controllers only
            continue
        slot = os.path.basename(os.path.realpath(dev))  # 0000:01:00.0
        try:
            vendor = int(_read(os.path.join(dev, "vendor")), 16)
        except ValueError:
            continue
        found.append({"slot": slot, "vendor": vendor, "boot": _read(os.path.join(dev, "boot_vga")) == "1"})
    out = []
    for g in found:
        pci_id = "pci-" + g["slot"].replace(":", "_").replace(".", "_")
        default = g["boot"] or (not any(x["boot"] for x in found) and g is found[0])
        out.append({"id": pci_id, "name": _short_name(g["slot"], g["vendor"]), "default": default, "vendor": g["vendor"],
                    "env": _env_for(g["vendor"], pci_id, default)})
    out.sort(key=lambda g: not g["default"])
    for g in out:  # Intel cards are integrated; so is an AMD one that shares the PC with a NVIDIA card
        g["integrated"] = g["vendor"] == INTEL or (g["vendor"] != NVIDIA and any(o["vendor"] == NVIDIA for o in out))
    _cache.update(t=time.monotonic(), gpus=out)
    return out


def has_choice():
    """True when there is more than one GPU: only then the GPU mode exists."""
    return len(gpus()) > 1


def chosen():
    """The GPU the apps use: the saved choice if that card is still there, else the default one."""
    cards = gpus()
    saved = _read(STATE_FILE)
    for g in cards:
        if g["id"] == saved:
            return g
    return cards[0] if cards else None


def _owned_keys():
    """Variables written by us the last time (only these are ever removed from the session)."""
    keys = set()
    for line in _read(ENV_FILE).splitlines():
        if "=" in line and not line.startswith("#"):
            keys.add(line.split("=", 1)[0].strip())
    return keys


def _systemctl(*args):
    try:
        return subprocess.run(["systemctl", "--user", *args], capture_output=True, timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


STEAM_FLATPAK = "com.valvesoftware.Steam"


def _keep_steam_off_the_variables():
    """The Steam client crashes at start (segfault) when the session forces a GPU with these variables. Games started from Steam
    can still use the card (Steam's launch options), so Steam, if installed as a Flatpak, simply does not receive them."""
    if not shutil.which("flatpak"):
        return
    try:
        if subprocess.run(["flatpak", "info", STEAM_FLATPAK], capture_output=True, timeout=10).returncode == 0:
            subprocess.run(["flatpak", "override", "--user", *[f"--unset-env={k}" for k in GPU_VARS], STEAM_FLATPAK],
                           capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass


def apply(gpu):
    """Makes `gpu` (an item of gpus()) the one the apps render on. Returns True if everything could be written."""
    ok = True
    old = _owned_keys()
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            f.write(gpu["id"])
        if gpu["env"]:
            os.makedirs(os.path.dirname(ENV_FILE), exist_ok=True)
            with open(ENV_FILE, "w") as f:
                f.write("# Written by asus-dial (GPU mode). Delete the file, or pick the default GPU there, to undo it.\n")
                for k, v in gpu["env"].items():
                    f.write(f"{k}={v}\n")
        elif os.path.exists(ENV_FILE):
            os.remove(ENV_FILE)
    except OSError:
        ok = False
    if gpu["env"]:
        _keep_steam_off_the_variables()
    stale = sorted(old - set(gpu["env"]))
    if stale:
        ok = _systemctl("unset-environment", *stale) and ok
    if gpu["env"]:
        ok = _systemctl("set-environment", *[f"{k}={v}" for k, v in gpu["env"].items()]) and ok
    return ok


def run_env(gpu=None):
    """os.environ plus the variables of the chosen GPU, for starting a program on it."""
    gpu = gpu or chosen()
    env = {k: v for k, v in os.environ.items() if k not in GPU_VARS}  # whatever GPU the session was started with
    env.update(gpu["env"] if gpu else {})
    return env

# ASUS Dial Linux for GNOME and KDE Plasma

**English** · [Español](#español) · [Italiano](#italiano)

---

# English

Unofficial driver for the **ASUS Dial** knob (found on ProArt StudioBook laptops) on Linux with **GNOME** or **KDE Plasma**, with an on-screen radial menu and 19 modes.

The kernel creates no input device for the dial. This program reads the raw data from `hidraw`, turns it into actions (scroll, volume, zoom…) and shows a menu and messages on screen.

> Tested on: ASUS ProArt StudioBook H5600QM, dial `0B05:0220`, with Ubuntu + GNOME 46 (X11) and CachyOS + **KDE Plasma 6.8 (Wayland)**.
> Other models with the same ID should work. The desktop is recognised by itself: nothing to configure (see *GNOME and KDE Plasma*).

> **Quick install:** run `./install.sh` (it does steps 3 and 4 below and asks for `sudo` once for step 2). The AI app installs its own dependencies later, by itself.

## How to use it

- **Rotate** the dial: does what the current mode says.
- **Short click**: the mode's action (play/pause, mute, zoom 100%, …).
- **Long press** (or press and rotate): opens the **radial menu**. Rotate to pick a mode and click to confirm (or hold, rotate and release).
- The chosen mode is remembered after a reboot.

## Modes

| Mode | Rotate | Click |
|---|---|---|
| ↕ **Scroll** | scrolls the page | middle click |
| 🔊 **Volume** | volume | click: mute; **double click: boost**, the sound jumps to 150% and the wheel can stay above 100% (double click again to go back) |
| ☀ **Brightness** | screen brightness | – |
| ⌨ **Keyboard** | keyboard backlight (levels 0–3) | off / back on |
| 🌙 **Night light** | night light (1700–4700 K), turns on by itself | on / off |
| 🔍 **Zoom** | in a browser: page zoom; **outside a browser: screen zoom** (GNOME magnifier or KWin's Zoom effect, up to 16×) | back to 100% |
| ▶ **Video** | seek ±5 seconds | play / pause |
| ⏩ **Speed** | video speed from 0.25× to 3× | back to 1× |
| ⏲ **Timer** | sets the minutes (1 per step up to 10, then 5) | start / cancel |
| 🗂 **Tabs** *(browser only)* | next / previous tab | – |
| 🔎 **Find** *(browser only)* | next / previous search result | opens find-in-page |
| 🪟 **Windows** | switches between windows (like Alt+Tab) | confirm / previous window |
| ↔ **Arrows** | left / right arrow keys | Enter |
| 🎲 **Dice** | picks the die (d4…d20) | rolls it, with an animation |
| 🏠 **House** | tilts a picture (see below) | – |
| 🤖 **AI** | picks the level: Low (MiniCPM5-2B), Medium (Llama 3.1 8B), High (DeepSeek-R1-Distill-Qwen-14B), **MAX** (Llama 3.3 70B with AirLLM, rainbow), **Custom** (any Ollama model you choose) | robot animation, then the **ASUS Dial AI** app opens with that model |
| ✨ **Rickroll** | – | a divine light show, then your default browser opens the video full screen |
| 🌐 **Language** | cycles English → Español → Italiano (default: English) | shows the current language |
| 🎮 **GPU** | picks one of the PC's graphics cards (only shown if the PC has two or more) | the card and whether it is integrated or dedicated; click makes your apps use it |
| 😴 **Sleep** | — | click starts a 3-second countdown, then the PC suspends; turning or clicking the wheel cancels it |
| ⏻ **Power off** | keep rotating clockwise to arm a 5-second shutdown countdown | – |

**Context-aware modes.** *Tabs* and *Find* show up in the menu only while the active window is a browser (Firefox, Chrome, Chromium, Brave, Vivaldi, Opera, Edge, LibreWolf, Epiphany, Zen, Floorp, Waterfox, Tor Browser). Outside a browser they disappear, and if one of them was your chosen mode the dial behaves like *Scroll* until you are back in the browser.

**Timer.** When time is up the system alarm sound plays and a giant 🍅 splats on your screen for 10 seconds, with a random message ("Timer expired!", "Completed!", "Finished!" or "BOO!", in the chosen language). Click the dial to stop it.

**Rickroll.** Click the dial in this mode: the screen dims, golden rays and sparkles fill it with heavenly light, the lyrics appear and, in a blinding white flash, your default browser opens a famous 1987 music video and puts it **full screen** (it presses `K` if autoplay was blocked, then `F`, so it needs a YouTube page; press `Esc` to leave). Change the video by editing `RICKROLL_URL` at the top of the `asus-dial` file.

**AI.** Rotate to pick the level (*Low* in green, *Medium* in yellow, *High* in red, *MAX* in rainbow letters), click to open the **ASUS Dial AI** app with that model. While the app is open, the dial's wheel keeps changing the model. Everything runs **locally** (the internet is only used for downloads): *Low* = MiniCPM5-2B (1.6 GB), *Medium* = Llama 3.1 8B (4.9 GB), *High* = DeepSeek-R1-Distill-Qwen-14B (9 GB, thinks before answering), **MAX** = Llama 3.3 70B run layer by layer with [AirLLM](https://github.com/lyogavin/airllm) (about 140 GB to download, then ~40 GB on disk, and **very slow**: it is meant to prove a 70B fits on a small GPU, not to chat fast). The app (`asus-dial-ai-app`) is a ChatGPT-like window: chats in a sidebar (saved in `~/.local/share/asus-dial-ai/chats`), answers that stream in, code blocks with a copy button, the model's reasoning in a collapsible box, a **voice mode** with a living orb (you talk, it answers aloud; click the orb to interrupt; the model's reasoning is switched off there for faster answers), **10 voice presets** (Aurora, Marco, Nova, Atlas, Pixel, Robo, Whisper, Narrator, Giant, Echo) with sliders for speed, pitch, volume and expressiveness, and a speaker button to hear the answers of the normal chat too and a **settings window** to change theme, accent colour, text size, roundness, background, orb style, animations, system prompt, creativity, voice language and more. **Nothing needs to be installed by hand**: the first time you use something, the app tells you what it needs and its size, asks once, and then installs it for your user only (no sudo): Ollama in `~/.local/ollama`; for MAX and voice a private Python 3.12 in `~/.local/share/asus-dial-ai/venv` with AirLLM, PyTorch, Whisper (speech to text) and Piper (text to speech), obtained with [uv](https://github.com/astral-sh/uv) (checksum verified). Without a working GPU driver everything runs on the CPU, which is much slower. On an NVIDIA hybrid laptop with the GPU switched off, `sudo prime-select on-demand` and a reboot enable it.

**Custom AI model.** After *MAX* there is a fifth level, **Custom**: it runs any model you want through Ollama. The first time you pick it the app asks for its name (`qwen3:8b`, `gemma3:4b`, `hf.co/user/repo:Q4_K_M`), or you can choose one you already have; change it whenever you like in *Settings → Chat*. If the model is missing, the app asks and downloads it the first time you write to it.


**The AI controls the PC.** In the chat and in the voice mode you can ask for what the dial does: *"lower the brightness and zoom 50%"*, *"volume to 30"*, *"next tab"*, *"timer of 10 minutes"*, *"night light on"*, *"roll a d20"*, *"lock the screen"*, *"use the integrated GPU"*... (Italian, English and Spanish). Usual commands are understood by the app itself and run instantly; for other requests the model is told about the same functions. The app talks to the driver through the socket `$XDG_RUNTIME_DIR/asus-dial.sock` (one JSON line: `{"do":"brightness","args":{"mode":"set","value":40}}`; `status` tells the current values). Switch it off in the app settings (*The AI can control the PC*). Power off / reboot are deliberately not available.

**GPU.** Only on a PC with two or more graphics cards (for example an integrated Radeon/Intel plus a dedicated NVIDIA): with a single GPU the mode does not exist, neither in the menu nor in the manager. Rotate to go through the cards (each shows its name and whether it is *integrated* or *dedicated*, and **✓ in use** on the current one), click to make your apps render on that card. It works the way GNOME's *Launch using Discrete Graphics Card* does, with no root: the choice is saved in `~/.config/environment.d/60-asus-dial-gpu.conf` (the PRIME render-offload variables) and given right away to everything the session starts from now on; apps that are already open keep the card they started on, and **everything** (the launcher too) follows after you log in again. Choosing the system's default card removes the variables. It does not power a card off. The Steam client (Flatpak) crashes at start when a GPU is forced on it, so choosing a card also tells Flatpak not to pass the variables to Steam; games started from Steam can still use the card through their launch options. From the terminal: `asus-dial-gpu list`, `asus-dial-gpu set 2`, and `asus-dial-gpu run <command>` to start one program on the chosen card at once.

**Language.** Menu, messages and timer texts are in **English by default**. The *Language* mode switches between English, Spanish and Italian; the choice is saved in `~/.config/asus-dial.lang`. To add a language, add it to `LANGS`, `LANG_NAMES`, `NAMES_L`, `TIMER_MESSAGES_L` and add a column to every entry of `STR` in the `asus-dial` file.

**House.** Shows a picture that tilts as you rotate. Set the path of your own image in `HOUSE_IMAGE` at the top of the `asus-dial` file; if the file is missing you just get an "image not found" message.

## GNOME and KDE Plasma

The same program runs on both desktops and finds out by itself which one it is on, at every start. Most modes work the same everywhere (keys, scrolling, volume, media, timer, GPU, lock); the ones that need the desktop use its own services (`asus_dial_desktop.py`):

| | GNOME | KDE Plasma |
|---|---|---|
| Screen brightness | Mutter / gnome-settings-daemon | PowerDevil (`org.kde.ScreenBrightness`), without Plasma's own OSD |
| Keyboard backlight | gnome-settings-daemon | PowerDevil (UPower as a fallback on both) |
| Night light | gsettings, schedule set to "all day" | KWin Night Light (`kwinrc`, mode *Always on*) |
| Screen zoom | GNOME magnifier | KWin **Zoom** effect |
| Which window has the focus (browser modes, Rickroll) | `xprop`: X11 windows only | a small **KWin script** that tells the dial over D-Bus: every window, **Wayland included** |
| On-screen menu and messages | X11 window, scaled by GNOME | X11 window (XWayland) scaled with `GDK_SCALE` from Plasma's scale; real KWin blur behind it when the theme uses blur |

On Plasma the browser modes (*Tabs*, *Find*) and the page zoom therefore know exactly when a browser has the focus, on Wayland too. Nothing is changed in Plasma's settings for good: the night light puts your own mode back when you turn it off, the KWin script is loaded only while the dial runs.

## Installation

### 1. Dependencies (Ubuntu / Debian)

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-pango-1.0 \
                 wireplumber x11-utils pulseaudio-utils xdg-utils gnome-terminal curl zstd python3-pil
```

- `wireplumber` (the `wpctl` command): volume.
- `x11-utils` (the `xprop` command): to tell whether the active window is a browser (on GNOME).
- `pulseaudio-utils` (the `paplay` command): timer sound.
- `xdg-utils`: opens the default browser.
- `gnome-terminal`, `curl`, `zstd`: for the AI mode (terminal, downloads, unpacking Ollama).
- `python3-pil` (Pillow): the frosted-glass blur of the themes (optional: without it the menu is just translucent).

On **Arch / CachyOS / Manjaro** (with GNOME or KDE Plasma):

```bash
sudo pacman -S --needed python-gobject python-cairo gtk3 wireplumber xorg-xprop xorg-xrdb libpulse xdg-utils curl zstd python-pillow
```

On KDE Plasma, `kreadconfig6`/`kwriteconfig6` (night light, zoom step) come with Plasma itself, and `kscreen-doctor` tells the dial the screen scale.

### 2. Permissions (once)

The program reads the dial from `/dev/hidraw*` and creates virtual keyboard/mouse events through `/dev/uinput`. The `input` group needs access:

```bash
sudo cp udev/99-asus-dial.rules /etc/udev/rules.d/
sudo usermod -aG input "$USER"
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=hidraw
sudo udevadm trigger --name-match=uinput
```

Then **log out and back in** (or reboot) so the `input` group takes effect.

### 3. The program

```bash
mkdir -p ~/.local/bin
cp asus-dial asus-dial-ai asus-dial-ai-app asus-dial-gpu asus-dial-manager asus-dial-welcome asus_dial_*.py ~/.local/bin/
chmod +x ~/.local/bin/asus-dial ~/.local/bin/asus-dial-ai ~/.local/bin/asus-dial-ai-app ~/.local/bin/asus-dial-gpu ~/.local/bin/asus-dial-manager ~/.local/bin/asus-dial-welcome
# launcher for the settings app (shows up in the applications menu)
mkdir -p ~/.local/share/applications
sed "s#^Exec=.*#Exec=$HOME/.local/bin/asus-dial-manager#" asus-dial-manager.desktop > ~/.local/share/applications/asus-dial-manager.desktop
# welcome animation at every login
mkdir -p ~/.config/autostart
sed "s#^Exec=.*#Exec=$HOME/.local/bin/asus-dial-welcome#" asus-dial-welcome.desktop > ~/.config/autostart/asus-dial-welcome.desktop
```

To try it right away, from a terminal: `~/.local/bin/asus-dial`.

### 4. Start at login

```bash
mkdir -p ~/.config/systemd/user
cp systemd/asus-dial.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now asus-dial
```

Status and logs:

```bash
systemctl --user status asus-dial
journalctl --user -u asus-dial -f
```

After every change to the file: `systemctl --user restart asus-dial`.

## Settings app (`asus-dial-manager`)

Open **ASUS Dial Manager** from the applications menu (or run `asus-dial-manager`). Changes are saved to `~/.config/asus-dial/config.json` and the dial picks them up by itself within a second — no restart needed.

- **Modes tab:** tick or untick any built-in mode to show or hide it in the circular menu, change the order with *Move up / Move down*, and *Restore defaults* to bring everything back (your custom modes stay).
- **Custom modes:** *Add custom mode…* creates a mode with a **name**, an **icon** (any emoji) and up to three actions made of keys: **click**, **rotate right** and **rotate left**. Examples: `p` (types the P key), `ctrl+shift+t`, or a series like `ctrl+c ctrl+v`. Use **Record** and press the keys on your keyboard to fill the field for you. Custom modes appear in the circular menu with the others (which grows if you have many).
- **Appearance tab:** how the circular menu and the on-screen messages look, with a live preview drawn by the same code as the dial. Pick a **preset** (Default, Glass, Neon, Rainbow ✨, Sunset, Paper, Halloween 🎃, **Christmas 🎄**, **Plasma 💠**, OLED black, Forest, Midnight, Ocean, Sakura, Ember) and tweak anything: **background** (plain color with opacity, a **cropped image** of yours, a spinning **rainbow** with sparkles, or the **Halloween 🎃** scene with ghosts, tombstones, a dancing skeleton, pumpkins, bats, a spider and cobwebs), **blur** (frosted glass: a blurred snapshot of what is behind the menu, taken when it opens), colors of the selected slice and of the text, **glow**, **glossy reflection**, **shadow** and **sparkles**. **Plasma 💠** looks like KDE's Breeze: on Plasma the menu and the messages are **real frosted glass** (KWin blurs what is behind them, like Plasma's own panels, also while they zoom in and out), with **Breeze icons** instead of emoji, the chosen mode big in the middle, and messages laid out like Plasma's OSD (icon, text, thin bar). It takes its colors and accent color from the desktop: *Plasma style* follows the system's light or dark look by itself (it changes as soon as you switch the desktop), or stays *Light* or *Dark* if you choose so. It works on GNOME too (light/dark and accent from the desktop portal).
- **Animations tab:** the menu and the on-screen messages **fade in/out smoothly**. Choose the **effect** for when they appear and for when they go away (none, fade, zoom, slide up, bounce, spin, or *fan*, a clock-style wipe), how long each takes (0–800 ms; 0 = instant), the **motion curve** (smooth, linear, overshoot, elastic, bouncy), whether the highlight **slides** from one slice to the next, and the transition used when you change tab in this app (crossfade, slide, cover, reveal…) or turn the app's animations off. A looping preview shows your choices.
- **General tab:** language of the dial and of the app, and everything about the **welcome** (see below), with a live preview.

**Welcome at login.** Every time you log in (4 seconds after the desktop loads) a character walks in along the bottom of the screen, waves, writes a message in a speech bubble — no voice, no sounds — bows and walks out (about 12 seconds). In the General tab you can switch it off, and choose: the **character** (human, robot, skeleton, or **your own PNG** — transparent background looks best), its **color**, a **rainbow style** (rainbow arc, color-cycling character, sparkles; it is always on when the theme is Rainbow), the **message** (`{name}` is replaced by the name; leave it empty for the default) and the **name** to greet (empty = “User”). With the Halloween theme the character wears a witch hat and a ghost, a pumpkin and bats appear; with the **Christmas** theme it wears a Santa hat and a lit tree, a snowman, presents and falling snow appear (the menu gets a candy-cane ring, twinkling lights, baubles, holly and a Santa hat too); the bubble follows the theme colors. **Play it now on screen** runs it immediately (`asus-dial-welcome --now`). It is started by the desktop through `~/.config/autostart/asus-dial-welcome.desktop`.

Key names: letters `a`–`z`, digits `0`–`9`, `f1`–`f12`, `enter`, `esc`, `tab`, `space`, `backspace`, `delete`, `insert`, `home`, `end`, `pageup`, `pagedown`, `up`, `down`, `left`, `right`, `minus`, `equal`, `comma`, `period`, `slash`, `semicolon`, `apostrophe`, `bracketleft`, `bracketright`, `backslash`, `grave`, `capslock`, `print`, `kpplus` (also `plus`), `kpminus`, `volumeup`, `volumedown`, `mute`, `playpause`, `next`, `previous`. Modifiers: `ctrl`, `shift`, `alt`, `super`. Keys are physical key positions (US-layout names): letters follow your layout, and `plus` is the keypad `+`, which works for browser zoom (`ctrl+plus`).

## Options

Put them on the `ExecStart=` line of the service (or on the command line):

| Option | Effect |
|---|---|
| `--invert` | reverses the rotation direction |
| `--menu-step N` | how far to rotate to move to the next menu item (default 8) |

## What you can change

Everything is at the top of the `asus-dial` file: mode names and icons (`NAMES`, `ICONS`), menu order (`MENU_ORDER`), timings (`HOLD_MS`, `TIMER_MAX`, `TOMATO_S`), alarm sound (`ALARM_SOUND`), browser list (`BROWSER_CLASSES`), browser-only modes (`BROWSER_ONLY`) and the shutdown command (`POWER_CMD`).

## Limitations and things to know

- **Browser detection on GNOME is X11 only.** It uses `xprop`: GNOME does not tell anybody which native Wayland window has the focus, so there the dial guesses from whether a browser is running. On **KDE Plasma** it is exact, on Wayland too (KWin script).
- **Video speed.** It changes the speed through MPRIS (the system media-control interface). If the browser does not allow that, the program falls back to the `Shift+<` and `Shift+>` keys of YouTube-style players, which only work if the video is in the active page, up to 2×.
- **Night light.** To make it visible at once, the program sets GNOME's schedule to "all day" (on Plasma: Night Light *Always on*) and saves your own settings in `~/.config/asus-dial.night.json`. When you turn it off it puts them back.
- **Screen zoom** uses the GNOME magnifier, or on Plasma the KWin Zoom effect, which zooms by its own step (1.2× by default, *System Settings → Accessibility → Zoom*): the dial counts its own steps from 1×, so if you also zoom with the keyboard shortcuts the factor it shows can differ.
- **Keyboard backlight** uses GNOME's power daemon or PowerDevil on Plasma (UPower if neither answers); it is meant for the ASUS keyboard with levels 0 to 3.
- **Scale on Plasma.** The menu is an X11 window and GTK 3 scales those only by whole numbers: at 190% it is drawn at 200%.
- *Power off* **really shuts the computer down**: rotate clockwise until the bar is full, then you have 5 seconds to cancel with a click or by rotating.
- It has been tested on a single laptop. If your dial has a different ID, change `HID_ID` in `asus-dial` (find it with `cat /sys/class/hidraw/hidraw*/device/uevent | grep HID_ID`).

## Uninstall

```bash
systemctl --user disable --now asus-dial
rm ~/.config/systemd/user/asus-dial.service ~/.local/bin/asus-dial ~/.local/bin/asus-dial-ai ~/.local/bin/asus-dial-manager ~/.local/bin/asus-dial-welcome ~/.local/bin/asus_dial_config.py ~/.local/bin/asus_dial_theme.py ~/.local/bin/asus_dial_characters.py ~/.local/bin/asus_dial_gpu.py ~/.local/bin/asus_dial_desktop.py ~/.local/bin/asus-dial-gpu ~/.config/environment.d/60-asus-dial-gpu.conf
rm -f ~/.local/share/applications/asus-dial-manager.desktop ~/.config/autostart/asus-dial-welcome.desktop
rm -rf ~/.config/asus-dial ~/.local/share/asus-dial
rm -f ~/.config/asus-dial.tool ~/.config/asus-dial.night.json ~/.config/asus-dial.lang ~/.config/asus-dial.ai
sudo rm /etc/udev/rules.d/99-asus-dial.rules
# optional, to also remove Ollama and the downloaded models:
rm -rf ~/.local/ollama ~/.ollama
```

## How it works (in short)

1. It reads `hidraw` reports (id 1: byte 1 bit 0 = button, bytes 2–3 = `int16` rotation, about 8–10 units per detent).
2. It turns rotation and clicks into events through a virtual `uinput` device, or calls system services (`wpctl`, D-Bus/MPRIS, GNOME or KDE Plasma).
3. It draws the menu, messages and animations with GTK 3 and Cairo, in transparent windows that let mouse clicks through.

## License

**MIT License — open source and free.** Anyone can use, copy, modify and share it, as long as the copyright notice is kept (see [`LICENSE`](LICENSE)).

Created by **ALEXLIONBIT** (human, red clothes, curly hair) together with **Claude** (an AI assistant made by Anthropic). The *About* tab of the settings app shows them saying hello.

---

# Español

Controlador no oficial para la rueda **ASUS Dial** (la de los portátiles ProArt StudioBook) en Linux con **GNOME** o **KDE Plasma**, con un menú circular en pantalla y 19 modos.

El kernel no crea ningún dispositivo de entrada para la rueda. Este programa lee los datos en bruto de `hidraw`, los convierte en acciones (desplazar, volumen, zoom…) y muestra un menú y mensajes en pantalla.

> Probado en: ASUS ProArt StudioBook H5600QM, rueda `0B05:0220`, con Ubuntu + GNOME 46 (X11) y CachyOS + **KDE Plasma 6.8 (Wayland)**.
> Otros modelos con el mismo identificador deberían funcionar. El escritorio se reconoce solo: no hay nada que configurar (ver *GNOME y KDE Plasma*).

## Cómo se usa

- **Girar** la rueda: hace lo que indica el modo actual.
- **Clic corto**: la acción del modo (reproducir/pausa, silenciar, zoom al 100 %, …).
- **Pulsación larga** (o pulsar y girar): abre el **menú circular**. Gira para elegir un modo y haz clic para confirmar (o mantén pulsado, gira y suelta).
- El modo elegido se recuerda después de reiniciar.

## Modos

| Modo | Girar | Clic |
|---|---|---|
| ↕ **Desplazar** | desplaza la página | clic central |
| 🔊 **Volumen** | volumen | clic: silenciar; **doble clic: boost**, el sonido salta al 150 % y la rueda puede seguir por encima del 100 % (otro doble clic para volver) |
| ☀ **Brillo** | brillo de la pantalla | – |
| ⌨ **Teclado** | retroiluminación del teclado (niveles 0–3) | apaga / vuelve a encender |
| 🌙 **Luz nocturna** | luz nocturna (1700–4700 K), se enciende sola | enciende / apaga |
| 🔍 **Zoom** | en el navegador: zoom de la página; **fuera del navegador: zoom de pantalla** (lupa de GNOME o efecto Zoom de KWin, hasta 16×) | vuelve al 100 % |
| ▶ **Vídeo** | avanza / retrocede 5 segundos | reproducir / pausa |
| ⏩ **Velocidad** | velocidad del vídeo de 0,25× a 3× | vuelve a 1× |
| ⏲ **Temporizador** | fija los minutos (1 por paso hasta 10, luego 5) | iniciar / cancelar |
| 🗂 **Pestañas** *(solo navegador)* | pestaña siguiente / anterior | – |
| 🔎 **Buscar** *(solo navegador)* | resultado siguiente / anterior | abre la búsqueda en la página |
| 🪟 **Ventanas** | cambia entre ventanas (como Alt+Tab) | confirmar / ventana anterior |
| ↔ **Flechas** | teclas de flecha izquierda / derecha | Intro |
| 🎲 **Dado** | elige el dado (d4…d20) | lo tira, con animación |
| 🏠 **Casa** | inclina una imagen (ver abajo) | – |
| 🤖 **IA** | elige el nivel: Bajo (MiniCPM5-2B), Medio (Llama 3.1 8B), Alto (DeepSeek-R1-Distill-Qwen-14B), **MAX** (Llama 3.3 70B con AirLLM, arcoíris), **Propio** (el modelo de Ollama que elijas) | animación de un robot y se abre la app **ASUS Dial AI** con ese modelo |
| ✨ **Rickroll** | – | un espectáculo de luz divina y luego tu navegador predeterminado abre el vídeo a pantalla completa |
| 🌐 **Idioma** | cambia entre English → Español → Italiano (por defecto: English) | muestra el idioma actual |
| 🎮 **GPU** | elige una de las tarjetas gráficas del PC (solo aparece si el PC tiene dos o más) | la tarjeta y si es integrada o dedicada; el clic hace que tus apps la usen |
| 😴 **Suspender** | — | el clic inicia una cuenta atrás de 3 s y el PC se suspende; girar o hacer clic en la rueda la cancela |
| ⏻ **Apagar** | sigue girando en sentido horario para activar una cuenta atrás de 5 segundos | – |

**Modos según el contexto.** *Pestañas* y *Buscar* aparecen en el menú solo cuando la ventana activa es un navegador (Firefox, Chrome, Chromium, Brave, Vivaldi, Opera, Edge, LibreWolf, Epiphany, Zen, Floorp, Waterfox, Tor Browser). Fuera del navegador desaparecen, y si uno de ellos era el modo elegido, la rueda se comporta como *Desplazar* hasta que vuelvas al navegador.

**Temporizador.** Al terminar el tiempo suena la alarma del sistema y un 🍅 gigante se estrella contra la pantalla durante 10 segundos, con un mensaje al azar («¡Temporizador agotado!», «¡Completado!», «¡Terminado!» o «¡BU!», en el idioma elegido). Un clic en la rueda lo detiene.

**Rickroll.** Haz clic en la rueda en este modo: la pantalla se oscurece, rayos dorados y destellos la llenan de luz celestial, aparece la letra y, con un destello blanco cegador, tu navegador predeterminado abre un famoso videoclip de 1987 y lo pone a **pantalla completa** (pulsa `K` si la reproducción automática estaba bloqueada y luego `F`, así que necesita una página de YouTube; pulsa `Esc` para salir). Para cambiar el vídeo, edita `RICKROLL_URL` al principio del archivo `asus-dial`.

**IA.** Gira para elegir el nivel (*Bajo* en verde, *Medio* en amarillo, *Alto* en rojo, *MAX* con letras arcoíris) y haz clic para abrir la app **ASUS Dial AI** con ese modelo; con la app abierta, la rueda sigue cambiando el modelo. Todo corre **en local** (internet solo para las descargas). **MAX** = Llama 3.3 70B ejecutado capa por capa con AirLLM (~140 GB de descarga, **muy lento**). La app es una ventana tipo ChatGPT con chats, **modo voz** con una esfera animada y ajustes para personalizarlo todo. **No hay que instalar nada a mano**: la primera vez la app te dice qué necesita y cuánto pesa, pregunta una vez e instala todo solo para tu usuario (sin sudo): Ollama, y para MAX y la voz un Python privado con AirLLM, PyTorch, Whisper y Piper.

**Modelo propio.** Después de *MAX* hay un quinto nivel, **Propio**: usa el modelo que quieras a través de Ollama. La primera vez que lo eliges la app te pide el nombre (`qwen3:8b`, `gemma3:4b`, `hf.co/usuario/repo:Q4_K_M`), o puedes elegir uno que ya tengas; se cambia cuando quieras en *Ajustes → Chat*. Si falta, la app te pregunta y lo descarga la primera vez que le escribes.


**La IA controla el PC.** En el chat y en el modo voz puedes pedir lo que hace la rueda: *"baja el brillo y zoom del 50%"*, *"volumen a 30"*, *"pestaña siguiente"*, *"temporizador de 10 minutos"*, *"luz nocturna"*, *"tira un dado"*, *"bloquea la pantalla"*... (italiano, inglés y español). Los comandos habituales los entiende la propia app y se ejecutan al instante; para el resto el modelo conoce las mismas funciones. La app habla con el controlador por el socket `$XDG_RUNTIME_DIR/asus-dial.sock`. Se desactiva en los ajustes de la app. Apagar y reiniciar no están disponibles a propósito.

**GPU.** Solo en un PC con dos o más tarjetas gráficas (por ejemplo una Radeon/Intel integrada y una NVIDIA dedicada): con una sola GPU el modo no existe, ni en el menú ni en el gestor. Gira para recorrer las tarjetas (cada una muestra su nombre y si es *integrada* o *dedicada*, y **✓ en uso** en la actual) y haz clic para que tus apps rendericen en esa tarjeta. Funciona como *Ejecutar con la tarjeta gráfica dedicada* de GNOME, sin root: la elección se guarda en `~/.config/environment.d/60-asus-dial-gpu.conf` (las variables de PRIME render offload) y se da al instante a todo lo que la sesión inicie desde ese momento; las apps ya abiertas conservan su tarjeta y **todo** (también el lanzador) la usa al volver a iniciar sesión. Elegir la tarjeta predeterminada del sistema quita las variables. No apaga ninguna tarjeta. El cliente de Steam (Flatpak) se cierra al iniciar si se le fuerza una GPU, así que al elegir una tarjeta también se indica a Flatpak que no le pase las variables a Steam; los juegos lanzados desde Steam pueden seguir usando la tarjeta con sus opciones de lanzamiento. Desde el terminal: `asus-dial-gpu list`, `asus-dial-gpu set 2` y `asus-dial-gpu run <comando>` para iniciar un programa en la tarjeta elegida al momento.

**Idioma.** El menú, los mensajes y los textos del temporizador están en **inglés por defecto**. El modo *Idioma* cambia entre inglés, español e italiano; la elección se guarda en `~/.config/asus-dial.lang`. Para añadir un idioma, añádelo a `LANGS`, `LANG_NAMES`, `NAMES_L`, `TIMER_MESSAGES_L` y añade una columna a cada entrada de `STR` en el archivo `asus-dial`.

**Casa.** Muestra una imagen que se inclina al girar. Pon la ruta de tu propia imagen en `HOUSE_IMAGE`, al principio del archivo `asus-dial`; si el archivo no existe solo verás el mensaje «imagen no encontrada».

## GNOME y KDE Plasma

El mismo programa funciona en los dos escritorios y averigua solo en cuál está, cada vez que arranca. La mayoría de los modos funcionan igual en todas partes (teclas, desplazamiento, volumen, multimedia, temporizador, GPU, bloqueo); los que necesitan el escritorio usan sus propios servicios (`asus_dial_desktop.py`):

| | GNOME | KDE Plasma |
|---|---|---|
| Brillo de pantalla | Mutter / gnome-settings-daemon | PowerDevil (`org.kde.ScreenBrightness`), sin el OSD de Plasma |
| Retroiluminación del teclado | gnome-settings-daemon | PowerDevil (UPower como respaldo en ambos) |
| Luz nocturna | gsettings, horario «todo el día» | Luz nocturna de KWin (`kwinrc`, modo *Siempre activa*) |
| Zoom de pantalla | lupa de GNOME | efecto **Zoom** de KWin |
| Qué ventana tiene el foco (modos del navegador, Rickroll) | `xprop`: solo ventanas X11 | un pequeño **script de KWin** que se lo dice al dial por D-Bus: todas las ventanas, **también en Wayland** |
| Menú y mensajes en pantalla | ventana X11, escalada por GNOME | ventana X11 (XWayland) escalada con `GDK_SCALE` según la escala de Plasma; desenfoque real de KWin detrás si el tema usa desenfoque |

Así, en Plasma los modos del navegador (*Pestañas*, *Buscar*) y el zoom de la página saben exactamente cuándo el navegador tiene el foco, también en Wayland. No se cambia nada de Plasma para siempre: la luz nocturna vuelve a tu modo al apagarla y el script de KWin solo está cargado mientras el dial funciona.

## Instalación

### 1. Dependencias (Ubuntu / Debian)

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-pango-1.0 \
                 wireplumber x11-utils pulseaudio-utils xdg-utils gnome-terminal curl zstd python3-pil
```

- `wireplumber` (comando `wpctl`): volumen.
- `x11-utils` (comando `xprop`): para saber si la ventana activa es un navegador (en GNOME).
- `pulseaudio-utils` (comando `paplay`): sonido del temporizador.
- `xdg-utils`: abre el navegador predeterminado.
- `gnome-terminal`, `curl`, `zstd`: para el modo IA (terminal, descargas, descomprimir Ollama).
- `python3-pil` (Pillow): el desenfoque de cristal esmerilado de los temas (opcional: sin él el menú es solo translúcido).

En **Arch / CachyOS / Manjaro** (con GNOME o KDE Plasma):

```bash
sudo pacman -S --needed python-gobject python-cairo gtk3 wireplumber xorg-xprop xorg-xrdb libpulse xdg-utils curl zstd python-pillow
```

En KDE Plasma, `kreadconfig6`/`kwriteconfig6` (luz nocturna, paso del zoom) vienen con Plasma, y `kscreen-doctor` le dice al dial la escala de la pantalla.

### 2. Permisos (una sola vez)

El programa lee la rueda desde `/dev/hidraw*` y crea eventos virtuales de teclado/ratón con `/dev/uinput`. El grupo `input` necesita acceso:

```bash
sudo cp udev/99-asus-dial.rules /etc/udev/rules.d/
sudo usermod -aG input "$USER"
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=hidraw
sudo udevadm trigger --name-match=uinput
```

Después **cierra la sesión y vuelve a entrar** (o reinicia) para que se aplique el grupo `input`.

### 3. El programa

```bash
mkdir -p ~/.local/bin
cp asus-dial asus-dial-ai asus-dial-ai-app asus-dial-gpu asus-dial-manager asus-dial-welcome asus_dial_*.py ~/.local/bin/
chmod +x ~/.local/bin/asus-dial ~/.local/bin/asus-dial-ai ~/.local/bin/asus-dial-ai-app ~/.local/bin/asus-dial-gpu ~/.local/bin/asus-dial-manager ~/.local/bin/asus-dial-welcome
# launcher for the settings app (shows up in the applications menu)
mkdir -p ~/.local/share/applications
sed "s#^Exec=.*#Exec=$HOME/.local/bin/asus-dial-manager#" asus-dial-manager.desktop > ~/.local/share/applications/asus-dial-manager.desktop
# welcome animation at every login
mkdir -p ~/.config/autostart
sed "s#^Exec=.*#Exec=$HOME/.local/bin/asus-dial-welcome#" asus-dial-welcome.desktop > ~/.config/autostart/asus-dial-welcome.desktop
```

Para probarlo enseguida, desde una terminal: `~/.local/bin/asus-dial`.

### 4. Inicio automático

```bash
mkdir -p ~/.config/systemd/user
cp systemd/asus-dial.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now asus-dial
```

Estado y registros:

```bash
systemctl --user status asus-dial
journalctl --user -u asus-dial -f
```

Tras cada cambio en el archivo: `systemctl --user restart asus-dial`.

## App de ajustes (`asus-dial-manager`)

Abre **ASUS Dial Manager** desde el menú de aplicaciones (o ejecuta `asus-dial-manager`). Los cambios se guardan en `~/.config/asus-dial/config.json` y la rueda los recoge sola en un segundo, sin reiniciar.

- **Pestaña Modos:** marca o desmarca cualquier modo integrado para mostrarlo u ocultarlo en el menú circular, cambia el orden con *Subir / Bajar* y usa *Restaurar valores* para recuperar todo (tus modos personalizados se conservan).
- **Modos personalizados:** *Añadir modo personalizado…* crea un modo con un **nombre**, un **icono** (cualquier emoji) y hasta tres acciones hechas de teclas: **clic**, **girar a la derecha** y **girar a la izquierda**. Ejemplos: `p` (pulsa la tecla P), `ctrl+shift+t` o una serie como `ctrl+c ctrl+v`. Con **Grabar** pulsas las teclas en tu teclado y rellena el campo por ti. Los modos personalizados aparecen en el menú circular junto a los demás (que se agranda si tienes muchos).
- **Pestaña Aspecto:** cómo se ven el menú circular y los mensajes en pantalla, con una vista previa en vivo dibujada por el mismo código que la rueda. Elige un **preajuste** (Predeterminado, Cristal, Neón, Arcoíris ✨, Atardecer, Papel, Halloween 🎃, **Navidad 🎄**, **Plasma 💠**, Negro OLED, Bosque, Medianoche, Océano, Sakura, Brasa) y ajusta lo que quieras: **fondo** (color liso con opacidad, una **imagen recortada** tuya, un **arcoíris** que gira con destellos o la escena de **Halloween 🎃** con fantasmas, tumbas, un esqueleto bailando, calabazas, murciélagos, una araña y telarañas), **desenfoque** (cristal esmerilado: una captura desenfocada de lo que hay detrás del menú, tomada al abrirlo), colores de la porción elegida y del texto, **luminiscencia**, **reflejo brillante**, **sombra** y **destellos**. **Plasma 💠** imita Breeze de KDE: en Plasma el menú y los mensajes son **cristal esmerilado de verdad** (KWin desenfoca lo que hay detrás, como en los paneles de Plasma, también mientras aparecen con zoom), con **iconos Breeze** en lugar de emoji, el modo elegido en grande en el centro y mensajes con el diseño del OSD de Plasma (icono, texto, barra fina). Toma los colores y el color de acento del escritorio: *Estilo Plasma* sigue solo el aspecto claro u oscuro del sistema (cambia en cuanto cambias el escritorio), o se queda en *Claro* u *Oscuro* si lo eliges. También funciona en GNOME (claro/oscuro y acento desde el portal del escritorio).
- **Pestaña Animaciones:** el menú y los mensajes en pantalla **aparecen y desaparecen con fluidez**. Elige el **efecto** al aparecer y al desaparecer (ninguno, fundido, zoom, subir deslizando, rebote, giro o *abanico*, un barrido tipo reloj), cuánto dura cada uno (0–800 ms; 0 = al instante), la **curva de movimiento** (suave, lineal, con rebasamiento, elástica, con rebotes), si el resaltado **se desliza** de una porción a la siguiente, y la transición al cambiar de pestaña en esta app (fundido cruzado, deslizar, cubrir, descubrir…) o desactivar las animaciones de la app. Una vista previa en bucle muestra tus elecciones.
- **Pestaña General:** idioma de la rueda y de la app, y todo lo de la **bienvenida** (ver abajo), con vista previa en vivo.

**Bienvenida al iniciar sesión.** Cada vez que inicias sesión (4 segundos después de cargar el escritorio) un personaje entra caminando por la parte inferior de la pantalla, saluda, escribe un mensaje en un bocadillo —sin voz y sin sonidos—, hace una reverencia y se va (unos 12 segundos). En la pestaña General puedes desactivarla y elegir: el **personaje** (humano, robot, esqueleto o **tu propio PNG** —queda mejor con fondo transparente—), su **color**, un **estilo arcoíris** (arco iris, personaje que cambia de color, destellos; siempre activo con el tema Arcoíris), el **mensaje** (`{name}` se sustituye por el nombre; vacío = mensaje predeterminado) y el **nombre** a saludar (vacío = «User»). Con el tema Halloween el personaje lleva sombrero de bruja y aparecen un fantasma, una calabaza y murciélagos; con el tema **Navidad** lleva un gorro de Papá Noel y aparecen un árbol iluminado, un muñeco de nieve, regalos y nieve cayendo (el menú recibe un aro de bastón de caramelo, luces parpadeantes, bolas, acebo y un gorro de Papá Noel); el bocadillo sigue los colores del tema. **Reproducir ahora en pantalla** la ejecuta al instante (`asus-dial-welcome --now`). El escritorio la inicia con `~/.config/autostart/asus-dial-welcome.desktop`.

Nombres de teclas: letras `a`–`z`, dígitos `0`–`9`, `f1`–`f12`, `enter`, `esc`, `tab`, `space`, `backspace`, `delete`, `insert`, `home`, `end`, `pageup`, `pagedown`, `up`, `down`, `left`, `right`, `minus`, `equal`, `comma`, `period`, `slash`, `semicolon`, `apostrophe`, `bracketleft`, `bracketright`, `backslash`, `grave`, `capslock`, `print`, `kpplus` (también `plus`), `kpminus`, `volumeup`, `volumedown`, `mute`, `playpause`, `next`, `previous`. Modificadores: `ctrl`, `shift`, `alt`, `super`. Las teclas son posiciones físicas (nombres del teclado US): las letras siguen tu distribución y `plus` es el `+` del teclado numérico, que sirve para el zoom del navegador (`ctrl+plus`).

## Opciones

Se ponen en la línea `ExecStart=` del servicio (o en la terminal):

| Opción | Efecto |
|---|---|
| `--invert` | invierte el sentido de giro |
| `--menu-step N` | cuánto hay que girar para pasar al siguiente elemento del menú (por defecto 8) |

## Qué se puede cambiar

Todo está al principio del archivo `asus-dial`: nombres e iconos de los modos (`NAMES`, `ICONS`), orden del menú (`MENU_ORDER`), tiempos (`HOLD_MS`, `TIMER_MAX`, `TOMATO_S`), sonido de la alarma (`ALARM_SOUND`), lista de navegadores (`BROWSER_CLASSES`), modos solo para navegador (`BROWSER_ONLY`) y el comando de apagado (`POWER_CMD`).

## Limitaciones y cosas que conviene saber

- **En GNOME la detección del navegador solo funciona con ventanas X11.** Usa `xprop`: GNOME no dice a nadie qué ventana Wayland nativa tiene el foco, así que allí el dial lo deduce de si hay un navegador abierto. En **KDE Plasma** es exacta, también en Wayland (script de KWin).
- **Velocidad de vídeo.** Cambia la velocidad mediante MPRIS (la interfaz de control multimedia del sistema). Si el navegador no lo permite, el programa recurre a las teclas `Mayús+<` y `Mayús+>` de los reproductores tipo YouTube, que solo funcionan si el vídeo está en la página activa y hasta 2×.
- **Luz nocturna.** Para que se vea al instante, el programa pone el horario de GNOME en «todo el día» (en Plasma: luz nocturna *Siempre activa*) y guarda tu configuración en `~/.config/asus-dial.night.json`. Al apagarla la restaura.
- **El zoom de pantalla** usa la lupa de GNOME o, en Plasma, el efecto Zoom de KWin, que amplía con su propio paso (1,2× por defecto, *Preferencias del sistema → Accesibilidad → Zoom*): el dial cuenta sus pasos desde 1×, así que si también haces zoom con los atajos de teclado el factor que muestra puede no coincidir.
- **La retroiluminación del teclado** usa el demonio de energía de GNOME o PowerDevil en Plasma (UPower si ninguno responde); está pensada para el teclado ASUS con niveles de 0 a 3.
- **Escala en Plasma.** El menú es una ventana X11 y GTK 3 solo las escala por números enteros: al 190 % se dibuja al 200 %.
- *Apagar* **apaga el ordenador de verdad**: gira en sentido horario hasta llenar la barra y tendrás 5 segundos para cancelar con un clic o girando.
- Solo se ha probado en un portátil. Si tu rueda tiene otro identificador, cambia `HID_ID` en `asus-dial` (lo encuentras con `cat /sys/class/hidraw/hidraw*/device/uevent | grep HID_ID`).

## Desinstalar

```bash
systemctl --user disable --now asus-dial
rm ~/.config/systemd/user/asus-dial.service ~/.local/bin/asus-dial ~/.local/bin/asus-dial-ai ~/.local/bin/asus-dial-manager ~/.local/bin/asus-dial-welcome ~/.local/bin/asus_dial_config.py ~/.local/bin/asus_dial_theme.py ~/.local/bin/asus_dial_characters.py ~/.local/bin/asus_dial_gpu.py ~/.local/bin/asus_dial_desktop.py ~/.local/bin/asus-dial-gpu ~/.config/environment.d/60-asus-dial-gpu.conf
rm -f ~/.local/share/applications/asus-dial-manager.desktop ~/.config/autostart/asus-dial-welcome.desktop
rm -rf ~/.config/asus-dial ~/.local/share/asus-dial
rm -f ~/.config/asus-dial.tool ~/.config/asus-dial.night.json ~/.config/asus-dial.lang ~/.config/asus-dial.ai
sudo rm /etc/udev/rules.d/99-asus-dial.rules
# opcional, para quitar también Ollama y los modelos descargados:
rm -rf ~/.local/ollama ~/.ollama
```

## Cómo funciona (resumen)

1. Lee los informes de `hidraw` (id 1: byte 1 bit 0 = botón, bytes 2–3 = rotación `int16`, unas 8–10 unidades por paso).
2. Convierte el giro y los clics en eventos con un dispositivo `uinput` virtual, o llama a servicios del sistema (`wpctl`, D-Bus/MPRIS, GNOME o KDE Plasma).
3. Dibuja el menú, los mensajes y las animaciones con GTK 3 y Cairo, en ventanas transparentes que dejan pasar los clics del ratón.

## Licencia

**Licencia MIT — código abierto y gratis.** Cualquiera puede usarlo, copiarlo, modificarlo y compartirlo, siempre que se conserve el aviso de copyright (ver [`LICENSE`](LICENSE)).

Creado por **ALEXLIONBIT** (humano, ropa roja, pelo rizado) junto con **Claude** (un asistente de IA hecho por Anthropic). La pestaña *Información* de la app de ajustes los muestra saludándose.

---

# Italiano

Driver non ufficiale per la **manopola ASUS Dial** (quella dei portatili ProArt StudioBook) su Linux con **GNOME** o **KDE Plasma**, con un menu circolare a schermo e 19 modalità.

Il kernel non crea nessun dispositivo di input per la manopola. Questo programma legge i dati grezzi da `hidraw`, li trasforma in azioni (scorrere, volume, zoom…) e mostra un menu e dei messaggi a schermo.

> Provato su: ASUS ProArt StudioBook H5600QM, manopola `0B05:0220`, con Ubuntu + GNOME 46 (X11) e CachyOS + **KDE Plasma 6.8 (Wayland)**.
> Altri modelli con lo stesso identificativo dovrebbero funzionare. Il desktop viene riconosciuto da solo: non c'è niente da configurare (vedi *GNOME e KDE Plasma*).

## Come si usa

- **Ruoti** la manopola: fa quello che dice la modalità attuale.
- **Clic breve**: l'azione della modalità (play/pausa, muto, zoom 100%, …).
- **Tieni premuto** (o premi e ruota): si apre il **menu circolare**. Ruoti per scegliere la modalità e clicchi per confermare (oppure tieni premuto, ruota e rilascia).
- La modalità scelta viene ricordata anche dopo il riavvio.

## Modalità

| Modalità | Ruotare | Clic |
|---|---|---|
| ↕ **Scorri** | scorre la pagina | clic centrale |
| 🔊 **Volume** | volume | clic: muto; **doppio clic: boost**, l'audio sale al 150% e la manopola può restare sopra il 100% (altro doppio clic per tornare indietro) |
| ☀ **Luminosità** | luminosità dello schermo | – |
| ⌨ **Tastiera** | retroilluminazione tastiera (livelli 0–3) | spegne / riaccende |
| 🌙 **Luce** | luce notturna (1700–4700 K), si accende da sola | accende / spegne |
| 🔍 **Zoom** | nel browser zoom della pagina; **fuori dal browser zoom dello schermo** (lente di GNOME o effetto Zoom di KWin, fino a 16×) | torna a 100% |
| ▶ **Video** | avanti / indietro di 5 secondi | play / pausa |
| ⏩ **Velocità** | velocità del video da 0,25× a 3× | torna a 1× |
| ⏲ **Timer** | imposta i minuti (1 a scatto fino a 10, poi 5) | avvia / annulla |
| 🗂 **Schede** *(solo browser)* | scheda successiva / precedente | – |
| 🔎 **Trova** *(solo browser)* | risultato successivo / precedente | apre la ricerca nella pagina |
| 🪟 **Finestre** | passa da una finestra all'altra (come Alt+Tab) | conferma / finestra precedente |
| ↔ **Frecce** | tasti freccia sinistra / destra | Invio |
| 🎲 **Dado** | sceglie il dado (d4…d20) | tira, con animazione |
| 🏠 **Casa** | inclina un'immagine (vedi sotto) | – |
| 🤖 **AI** | sceglie il livello: Basso (MiniCPM5-2B), Medio (Llama 3.1 8B), Alto (DeepSeek-R1-Distill-Qwen-14B), **MAX** (Llama 3.3 70B con AirLLM, arcobaleno), **Custom** (il modello di Ollama che scegli tu) | animazione di un robot, poi si apre l'app **ASUS Dial AI** con quel modello |
| ✨ **Rickroll** | – | uno spettacolo di luce divina, poi il browser predefinito apre il video a schermo intero |
| 🌐 **Lingua** | passa da English → Español → Italiano (predefinita: English) | mostra la lingua attuale |
| 🎮 **GPU** | sceglie una delle schede grafiche del PC (compare solo se il PC ne ha due o più) | la scheda e se è integrata o dedicata; il clic fa usare quella alle tue app |
| 😴 **Sospendi** | — | il clic avvia un conto alla rovescia di 3 s e il PC va in sospensione; girare o cliccare la manopola annulla |
| ⏻ **Arresta** | ruotando a lungo in senso orario spegne il PC dopo un conto alla rovescia di 5 secondi | – |

**Modalità che dipendono dal contesto.** *Schede* e *Trova* compaiono nel menu solo quando la finestra attiva è un browser (Firefox, Chrome, Chromium, Brave, Vivaldi, Opera, Edge, LibreWolf, Epiphany, Zen, Floorp, Waterfox, Tor Browser). Fuori dal browser spariscono, e se erano la modalità scelta la manopola si comporta come *Scorri* finché non torni nel browser.

**Timer.** Alla fine suona la sveglia di sistema e un 🍅 gigante si spiaccica sullo schermo per 10 secondi, con una scritta a caso («Timer scaduto!», «Completato!», «Finito!», «BOO!», nella lingua scelta). Un clic sulla manopola ferma tutto.

**Rickroll.** Clicca la manopola in questa modalità: lo schermo si oscura, raggi dorati e scintille lo riempiono di luce divina, compare il testo della canzone e, con un lampo bianco accecante, il browser predefinito apre un famoso video musicale del 1987 e lo mette a **schermo intero** (preme `K` se la riproduzione automatica era bloccata, poi `F`, quindi serve una pagina di YouTube; premi `Esc` per uscire). Per cambiare il video modifica `RICKROLL_URL` in cima al file `asus-dial`.

**AI.** Ruota per scegliere il livello (*Basso* in verde, *Medio* in giallo, *Alto* in rosso, *MAX* con le lettere arcobaleno) e clicca per aprire l'app **ASUS Dial AI** con quel modello; con l'app aperta la rotella continua a cambiare modello. Tutto gira **in locale** (internet serve solo per i download). *Basso* = MiniCPM5-2B (1,6 GB), *Medio* = Llama 3.1 8B (4,9 GB), *Alto* = DeepSeek-R1-Distill-Qwen-14B (9 GB, ragiona prima di rispondere), **MAX** = Llama 3.3 70B eseguito strato per strato con [AirLLM](https://github.com/lyogavin/airllm) (circa 140 GB da scaricare, poi ~40 GB su disco, e **lentissimo**). L'app (`asus-dial-ai-app`) è una finestra stile ChatGPT: chat nella barra laterale, risposte in streaming, blocchi di codice con tasto copia, il ragionamento del modello in un riquadro richiudibile, la **modalità vocale** con una sfera animata (parli tu, risponde a voce; clicca la sfera per interromperla; qui il ragionamento del modello è disattivato per rispondere prima), **10 voci preimpostate** (Aurora, Marco, Nova, Atlas, Pixel, Robo, Whisper, Narratore, Gigante, Eco) con cursori per velocità, tono, volume ed espressività, e un tasto altoparlante per sentire a voce anche le risposte della chat normale e le **impostazioni** per cambiare tema, colore, dimensione del testo, sfondo, sfera, animazioni, istruzioni di sistema, creatività, lingua della voce e altro. **Non devi installare niente a mano**: la prima volta che usi una cosa l'app ti dice cosa serve e quanto pesa, chiede una volta sola e poi installa tutto solo per il tuo utente (senza sudo): Ollama in `~/.local/ollama`; per MAX e la voce un Python 3.12 privato in `~/.local/share/asus-dial-ai/venv` con AirLLM, PyTorch, Whisper (voce→testo) e Piper (testo→voce), ottenuto con [uv](https://github.com/astral-sh/uv) (checksum verificato). Senza un driver GPU funzionante tutto gira sul processore, molto più lento. Su un portatile ibrido NVIDIA con la GPU spenta, `sudo prime-select on-demand` e un riavvio la attivano.

**Modello custom.** Dopo *MAX* c'è un quinto livello, **Custom**: usa il modello che vuoi tramite Ollama. La prima volta che lo scegli l'app ti chiede il nome (`qwen3:8b`, `gemma3:4b`, `hf.co/utente/repo:Q4_K_M`), oppure puoi sceglierne uno che hai già; si cambia quando vuoi in *Impostazioni → Chat*. Se manca, l'app te lo chiede e lo scarica la prima volta che le scrivi.


**L'AI controlla il PC.** In chat e in modalità vocale puoi chiedere quello che fa la rotella: *"abbassa la luminosità e zoomma del 50%"*, *"volume a 30"*, *"scheda successiva"*, *"timer di 10 minuti"*, *"accendi la luce notturna"*, *"tira un dado"*, *"blocca lo schermo"*... (italiano, inglese e spagnolo). I comandi comuni li capisce l'app da sola e li esegue subito; per le altre richieste il modello conosce le stesse funzioni. L'app parla col driver tramite il socket `$XDG_RUNTIME_DIR/asus-dial.sock`. Si disattiva nelle impostazioni dell'app. Spegnimento e riavvio non sono disponibili di proposito.

**GPU.** Solo su un PC con due o più schede grafiche (per esempio una Radeon/Intel integrata e una NVIDIA dedicata): con una sola GPU la modalità non esiste, né nel menu né nel gestore. Ruota per scorrere le schede (ognuna mostra il nome e se è *integrata* o *dedicata*, e **✓ in uso** su quella attuale) e clicca per far usare quella scheda alle tue app. Funziona come *Avvia con la scheda grafica dedicata* di GNOME, senza root: la scelta è salvata in `~/.config/environment.d/60-asus-dial-gpu.conf` (le variabili del PRIME render offload) e data subito a tutto ciò che la sessione avvia da quel momento; le app già aperte tengono la scheda con cui sono partite e **tutto** (anche il lanciatore) la usa dopo un nuovo accesso. Scegliere la scheda predefinita del sistema toglie le variabili. Non spegne nessuna scheda. Il client di Steam (Flatpak) va in crash all'avvio se gli si forza una GPU, quindi scegliendo una scheda si dice anche a Flatpak di non passare le variabili a Steam; i giochi avviati da Steam possono comunque usare la scheda con le loro opzioni di avvio. Da terminale: `asus-dial-gpu list`, `asus-dial-gpu set 2` e `asus-dial-gpu run <comando>` per avviare subito un programma sulla scheda scelta.

**Lingua.** Menu, messaggi e testi del timer sono in **inglese per impostazione predefinita**. La modalità *Lingua* passa tra inglese, spagnolo e italiano; la scelta viene salvata in `~/.config/asus-dial.lang`. Per aggiungere una lingua, aggiungila a `LANGS`, `LANG_NAMES`, `NAMES_L`, `TIMER_MESSAGES_L` e aggiungi una colonna a ogni voce di `STR` nel file `asus-dial`.

**Casa.** Mostra un'immagine che si inclina con la manopola. Metti il percorso della tua immagine in `HOUSE_IMAGE` in cima al file `asus-dial`; se il file non c'è, compare solo il messaggio «Immagine non trovata».

## GNOME e KDE Plasma

Lo stesso programma funziona su entrambi i desktop e capisce da solo su quale si trova, a ogni avvio. Quasi tutte le modalità funzionano allo stesso modo ovunque (tasti, scorrimento, volume, multimedia, timer, GPU, blocco); quelle che hanno bisogno del desktop usano i suoi servizi (`asus_dial_desktop.py`):

| | GNOME | KDE Plasma |
|---|---|---|
| Luminosità dello schermo | Mutter / gnome-settings-daemon | PowerDevil (`org.kde.ScreenBrightness`), senza l'OSD di Plasma |
| Retroilluminazione tastiera | gnome-settings-daemon | PowerDevil (UPower come riserva su entrambi) |
| Luce notturna | gsettings, orario «tutto il giorno» | Luce notturna di KWin (`kwinrc`, modalità *Sempre attiva*) |
| Zoom dello schermo | lente di GNOME | effetto **Zoom** di KWin |
| Quale finestra ha il focus (modalità del browser, Rickroll) | `xprop`: solo finestre X11 | un piccolo **script di KWin** che lo dice al dial via D-Bus: tutte le finestre, **anche su Wayland** |
| Menu e messaggi a schermo | finestra X11, scalata da GNOME | finestra X11 (XWayland) scalata con `GDK_SCALE` secondo la scala di Plasma; vera sfocatura di KWin dietro se il tema la usa |

Così su Plasma le modalità del browser (*Schede*, *Trova*) e lo zoom della pagina sanno esattamente quando il browser ha il focus, anche su Wayland. Nelle impostazioni di Plasma non cambia niente per sempre: la luce notturna torna alla tua modalità quando la spegni e lo script di KWin è caricato solo finché il dial è in funzione.

## Installazione

### 1. Dipendenze (Ubuntu / Debian)

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-pango-1.0 \
                 wireplumber x11-utils pulseaudio-utils xdg-utils gnome-terminal curl zstd python3-pil
```

- `wireplumber` (comando `wpctl`): volume.
- `x11-utils` (comando `xprop`): per capire se la finestra attiva è un browser (su GNOME).
- `pulseaudio-utils` (comando `paplay`): suono del timer.
- `xdg-utils`: apre il browser predefinito.
- `gnome-terminal`, `curl`, `zstd`: per la modalità AI (terminale, download, estrazione di Ollama).
- `python3-pil` (Pillow): la sfocatura a vetro smerigliato dei temi (facoltativo: senza, il menu è solo semitrasparente).

Su **Arch / CachyOS / Manjaro** (con GNOME o KDE Plasma):

```bash
sudo pacman -S --needed python-gobject python-cairo gtk3 wireplumber xorg-xprop xorg-xrdb libpulse xdg-utils curl zstd python-pillow
```

Su KDE Plasma `kreadconfig6`/`kwriteconfig6` (luce notturna, passo dello zoom) arrivano con Plasma, e `kscreen-doctor` dice al dial la scala dello schermo.

### 2. Permessi (una volta sola)

Il programma legge la manopola da `/dev/hidraw*` e crea tastiera/mouse virtuali con `/dev/uinput`. Serve il permesso al gruppo `input`:

```bash
sudo cp udev/99-asus-dial.rules /etc/udev/rules.d/
sudo usermod -aG input "$USER"
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=hidraw
sudo udevadm trigger --name-match=uinput
```

Poi **esci e rientra dalla sessione** (o riavvia) perché il gruppo `input` venga applicato.

### 3. Programma

```bash
mkdir -p ~/.local/bin
cp asus-dial asus-dial-ai asus-dial-ai-app asus-dial-gpu asus-dial-manager asus-dial-welcome asus_dial_*.py ~/.local/bin/
chmod +x ~/.local/bin/asus-dial ~/.local/bin/asus-dial-ai ~/.local/bin/asus-dial-ai-app ~/.local/bin/asus-dial-gpu ~/.local/bin/asus-dial-manager ~/.local/bin/asus-dial-welcome
# launcher for the settings app (shows up in the applications menu)
mkdir -p ~/.local/share/applications
sed "s#^Exec=.*#Exec=$HOME/.local/bin/asus-dial-manager#" asus-dial-manager.desktop > ~/.local/share/applications/asus-dial-manager.desktop
# welcome animation at every login
mkdir -p ~/.config/autostart
sed "s#^Exec=.*#Exec=$HOME/.local/bin/asus-dial-welcome#" asus-dial-welcome.desktop > ~/.config/autostart/asus-dial-welcome.desktop
```

Per provarlo subito, da terminale: `~/.local/bin/asus-dial`.

### 4. Avvio automatico

```bash
mkdir -p ~/.config/systemd/user
cp systemd/asus-dial.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now asus-dial
```

Controllo e log:

```bash
systemctl --user status asus-dial
journalctl --user -u asus-dial -f
```

Dopo ogni modifica al file: `systemctl --user restart asus-dial`.

## App di gestione (`asus-dial-manager`)

Apri **ASUS Dial Manager** dal menu delle applicazioni (oppure esegui `asus-dial-manager`). Le modifiche vengono salvate in `~/.config/asus-dial/config.json` e la manopola le legge da sola entro un secondo, senza riavviare.

- **Scheda Modalità:** spunta o togli la spunta a qualsiasi modalità predefinita per mostrarla o nasconderla nel menu circolare, cambia l'ordine con *Su / Giù* e usa *Ripristina predefiniti* per rimettere tutto (le tue modalità personalizzate restano).
- **Modalità personalizzate:** *Aggiungi modalità personalizzata…* crea una modalità con un **nome**, un'**icona** (qualsiasi emoji) e fino a tre azioni fatte di tasti: **clic**, **ruota a destra** e **ruota a sinistra**. Esempi: `p` (preme il tasto P), `ctrl+shift+t`, oppure una serie come `ctrl+c ctrl+v`. Con **Registra** premi i tasti sulla tastiera e il campo si compila da solo. Le modalità personalizzate compaiono nel menu circolare insieme alle altre (che si allarga se sono tante).
- **Scheda Aspetto:** come appaiono il menu circolare e i messaggi a schermo, con un'anteprima in diretta disegnata dallo stesso codice della manopola. Scegli un **preset** (Predefinito, Vetro, Neon, Arcobaleno ✨, Tramonto, Carta, Halloween 🎃, **Natale 🎄**, **Plasma 💠**, Nero OLED, Foresta, Mezzanotte, Oceano, Sakura, Brace) e regola quello che vuoi: **sfondo** (colore pieno con opacità, una tua **immagine ritagliata**, un **arcobaleno** che gira con scintille oppure la scena di **Halloween 🎃** con fantasmi, tombe, uno scheletro che balla, zucche, pipistrelli, un ragno e ragnatele), **sfocatura** (vetro smerigliato: una foto sfocata di ciò che c'è dietro il menu, scattata quando si apre), colori della fetta selezionata e del testo, **luminescenza**, **riflesso lucido**, **ombra** e **scintille**. **Plasma 💠** riprende Breeze di KDE: su Plasma il menu e i messaggi sono **vero vetro smerigliato** (KWin sfoca quello che c'è dietro, come nei pannelli di Plasma, anche mentre compaiono con lo zoom), con le **icone Breeze** al posto delle emoji, la modalità scelta in grande al centro e i messaggi impaginati come l'OSD di Plasma (icona, testo, barra sottile). Prende colori e colore d'accento dal desktop: *Stile Plasma* segue da solo l'aspetto chiaro o scuro del sistema (cambia appena cambi il desktop), oppure resta *Chiaro* o *Scuro* se lo scegli tu. Funziona anche su GNOME (chiaro/scuro e accento dal portale del desktop).
- **Scheda Animazioni:** il menu e i messaggi a schermo **compaiono e spariscono in modo fluido**. Scegli l'**effetto** per quando compaiono e per quando se ne vanno (nessuno, dissolvenza, zoom, scorrimento verso l'alto, rimbalzo, rotazione oppure *ventaglio*, un'apertura a lancette), quanto dura ciascuno (0–800 ms; 0 = subito), la **curva di movimento** (morbida, lineare, con sorpasso, elastica, a rimbalzi), se l'evidenziazione **scivola** da una fetta all'altra e la transizione quando cambi scheda in questa app (dissolvenza incrociata, scorrimento, sovrapposizione, scopri…) oppure spegnere le animazioni dell'app. Un'anteprima in loop mostra le tue scelte.
- **Scheda Generale:** lingua della manopola e dell'app, e tutto ciò che riguarda il **benvenuto** (vedi sotto), con anteprima in diretta.

**Benvenuto all'accesso.** Ogni volta che accedi (4 secondi dopo il caricamento del desktop) un personaggio entra camminando lungo il bordo basso dello schermo, saluta, scrive un messaggio in un fumetto — senza voce e senza suoni —, fa un inchino ed esce (circa 12 secondi). Nella scheda Generale puoi spegnerlo e scegliere: il **personaggio** (umano, robot, scheletro o **un tuo PNG** — viene meglio con lo sfondo trasparente), il suo **colore**, uno **stile arcobaleno** (arcobaleno, personaggio che cambia colore, scintille; è sempre attivo con il tema Arcobaleno), il **messaggio** (`{name}` viene sostituito dal nome; vuoto = messaggio predefinito) e il **nome** da salutare (vuoto = «User»). Con il tema Halloween il personaggio indossa il cappello da strega e compaiono un fantasma, una zucca e dei pipistrelli; con il tema **Natale** indossa un cappello da Babbo Natale e compaiono un albero illuminato, un pupazzo di neve, regali e neve che cade (il menu riceve un anello a bastoncino di zucchero, luci che lampeggiano, palline, agrifoglio e un cappello da Babbo Natale); il fumetto segue i colori del tema. **Riproduci ora sullo schermo** lo esegue subito (`asus-dial-welcome --now`). Lo avvia il desktop con `~/.config/autostart/asus-dial-welcome.desktop`.

Nomi dei tasti: lettere `a`–`z`, cifre `0`–`9`, `f1`–`f12`, `enter`, `esc`, `tab`, `space`, `backspace`, `delete`, `insert`, `home`, `end`, `pageup`, `pagedown`, `up`, `down`, `left`, `right`, `minus`, `equal`, `comma`, `period`, `slash`, `semicolon`, `apostrophe`, `bracketleft`, `bracketright`, `backslash`, `grave`, `capslock`, `print`, `kpplus` (anche `plus`), `kpminus`, `volumeup`, `volumedown`, `mute`, `playpause`, `next`, `previous`. Modificatori: `ctrl`, `shift`, `alt`, `super`. I tasti sono posizioni fisiche (nomi della tastiera US): le lettere seguono il tuo layout e `plus` è il `+` del tastierino numerico, che va bene per lo zoom del browser (`ctrl+plus`).

## Opzioni

Si danno sulla riga `ExecStart=` del servizio (o da terminale):

| Opzione | Effetto |
|---|---|
| `--invert` | inverte il verso di rotazione |
| `--menu-step N` | quanto ruotare per passare alla voce successiva del menu (predefinito 8) |

## Cosa si può cambiare

Tutto è in cima al file `asus-dial`: nomi e icone delle modalità (`NAMES`, `ICONS`), ordine nel menu (`MENU_ORDER`), tempi (`HOLD_MS`, `TIMER_MAX`, `TOMATO_S`), suono della sveglia (`ALARM_SOUND`), elenco dei browser (`BROWSER_CLASSES`), modalità solo-browser (`BROWSER_ONLY`) e comando di spegnimento (`POWER_CMD`).

## Limiti e cose da sapere

- **Su GNOME il browser si riconosce solo nelle finestre X11.** Si usa `xprop`: GNOME non dice a nessuno quale finestra Wayland nativa ha il focus, quindi lì il dial lo deduce dal fatto che un browser sia aperto. Su **KDE Plasma** è esatto, anche su Wayland (script di KWin).
- **Velocità video.** Cambia la velocità tramite MPRIS (il controllo multimediale di sistema). Se il browser non lo permette, il programma passa ai tasti `Shift+<` e `Shift+>` dei lettori tipo YouTube, che funzionano solo se il video è nella pagina attiva e fino a 2×.
- **Luce notturna.** Per vederla subito il programma imposta il programma di GNOME su «tutto il giorno» (su Plasma: luce notturna *Sempre attiva*) e salva le tue impostazioni in `~/.config/asus-dial.night.json`. Quando la spegni le rimette com'erano.
- **Zoom dello schermo** usa la lente di GNOME oppure, su Plasma, l'effetto Zoom di KWin, che ingrandisce col suo passo (1,2× di default, *Impostazioni di sistema → Accessibilità → Zoom*): il dial conta i suoi passi da 1×, quindi se fai zoom anche con le scorciatoie da tastiera il fattore mostrato può non coincidere.
- **Retroilluminazione tastiera** usa il demone energia di GNOME o PowerDevil su Plasma (UPower se nessuno dei due risponde); è pensata per la tastiera ASUS con livelli da 0 a 3.
- **Scala su Plasma.** Il menu è una finestra X11 e GTK 3 le scala solo per numeri interi: al 190% viene disegnato al 200%.
- La modalità *Arresta* **spegne davvero il computer**: ruota in senso orario fino alla barra piena, poi hai 5 secondi per annullare con un clic o ruotando.
- Il programma è provato su un solo portatile. Se la tua manopola ha un identificativo diverso, cambia `HID_ID` in `asus-dial` (lo trovi con `cat /sys/class/hidraw/hidraw*/device/uevent | grep HID_ID`).

## Disinstallare

```bash
systemctl --user disable --now asus-dial
rm ~/.config/systemd/user/asus-dial.service ~/.local/bin/asus-dial ~/.local/bin/asus-dial-ai ~/.local/bin/asus-dial-manager ~/.local/bin/asus-dial-welcome ~/.local/bin/asus_dial_config.py ~/.local/bin/asus_dial_theme.py ~/.local/bin/asus_dial_characters.py ~/.local/bin/asus_dial_gpu.py ~/.local/bin/asus_dial_desktop.py ~/.local/bin/asus-dial-gpu ~/.config/environment.d/60-asus-dial-gpu.conf
rm -f ~/.local/share/applications/asus-dial-manager.desktop ~/.config/autostart/asus-dial-welcome.desktop
rm -rf ~/.config/asus-dial ~/.local/share/asus-dial
rm -f ~/.config/asus-dial.tool ~/.config/asus-dial.night.json ~/.config/asus-dial.lang ~/.config/asus-dial.ai
sudo rm /etc/udev/rules.d/99-asus-dial.rules
# facoltativo, per togliere anche Ollama e i modelli scaricati:
rm -rf ~/.local/ollama ~/.ollama
```

## Come funziona (in breve)

1. Legge i rapporti di `hidraw` (id 1: byte 1 bit 0 = pulsante, byte 2-3 = rotazione `int16`, circa 8-10 unità per scatto).
2. Trasforma rotazione e clic in eventi con un dispositivo `uinput` virtuale oppure chiama servizi di sistema (`wpctl`, D-Bus/MPRIS, GNOME o KDE Plasma).
3. Disegna menu, messaggi e animazioni con GTK 3 e Cairo, in finestre trasparenti che non intercettano il mouse.

## Licenza

**Licenza MIT — open source e gratis.** Chiunque può usarlo, copiarlo, modificarlo e condividerlo, purché resti l'avviso di copyright (vedi [`LICENSE`](LICENSE)).

Creato da **ALEXLIONBIT** (umano, vestito di rosso, capelli ricci) insieme a **Claude** (un assistente AI creato da Anthropic). La scheda *Informazioni* dell'app di impostazioni li mostra mentre si salutano.

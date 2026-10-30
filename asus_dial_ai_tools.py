"""What the AI can do on the PC: the functions of the ASUS Dial, by voice or by chat.

Two ways in, both ending in the same calls to the dial driver (asus-dial, its socket asus-dial.sock):

  * quick(text): understands the usual commands in Italian, English and Spanish ("abbassa la luminosità e zoomma del 50%")
    by itself, so they run at once without waiting for the language model;
  * PROMPT + ToolFilter: for everything else the model is told about the same functions and writes lines like
    [[volume {"mode":"set","value":30}]]; they are taken out of the answer and executed.
"""
import json
import os
import re
import socket
import unicodedata

SOCKET = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "asus-dial.sock")


def call(do, **args):
    """Asks the dial driver to do something. Returns its answer dict ({"ok": bool, ...})."""
    try:
        c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        c.settimeout(6)
        c.connect(SOCKET)
        c.sendall(json.dumps({"do": do, "args": args}).encode())
        c.shutdown(socket.SHUT_WR)
        out = json.loads(c.makefile().readline())
        c.close()
        return out
    except (OSError, ValueError):
        return {"ok": False, "error": "dial"}


# ------------------------------------------------------------------------------------------------ for the model
PROMPT = """You can control the user's PC through the ASUS Dial. If the user asks for one of these actions, begin your answer with one line per action, \
written exactly like [[volume {"mode":"set","value":30}]], then say in one short sentence what you did. Use only these tools, never invent others, \
and use none when the user is just talking.
- volume {"mode": "set|up|down|mute|unmute|toggle", "value": 0-150}   (above 100 only if asked: it may distort)
- brightness {"mode": "set|up|down", "value": 0-100}   (screen brightness; set = absolute, up/down = change by value)
- zoom {"percent": 150} or {"mode": "in|out|reset"}   (100 = normal; "zoom 50%" means 50% bigger = 150)
- scroll {"direction": "up|down", "amount": 5}
- media {"action": "play|pause|play_pause|next|previous|seek|speed", "seconds": 10, "factor": 1.5}
- tab {"action": "next|previous|new|close|reopen"}   (browser tabs)
- timer {"minutes": 10} or {"cancel": true}
- night_light {"state": "on|off|toggle", "kelvin": 3400}
- keyboard_light {"level": 0-3}
- windows {"action": "switch|next|previous"}
- find {"action": "open|next|previous"}
- dice {"sides": 6}
- gpu {"which": "integrated|dedicated|default"}
- lock {}
- suspend {}   (put the PC to sleep after 3 seconds)
- mode {"name": "scroll|volume|brightness|zoom|video|tabs|arrows|dice|timer|speed|night|windows|find|keylight|language|ai|gpu"}   (what the dial wheel does)
- status {}   (current volume, brightness, ...)"""

_ACTION_WORDS = re.compile(r"volum|audio|suono|sound|sonido|luminos|bright|brillo|zoom|ingrand|rimpicc|scorri|scroll|scheda|schede|tab\b|pestana|timer|temporizador|"
                          r"luce|night|luz|sospen|suspen|stand ?by|dormire|sleep|retroillumin|tastiera|keyboard|teclado|finestra|window|ventana|dado|dice|gpu|scheda video|blocca|lock|"
                          r"pausa|pause|play|riproduc|traccia|canzone|song|track|musica|music|rotella|manopola|dial|rueda|muto|mute|silenz|schermo|screen|pantalla")
_CALL = re.compile(r"\[\[\s*([a-z_]+)\s*(\{.*?\})?\s*\]\]", re.S)
TOOL_NAMES = {"volume", "brightness", "zoom", "scroll", "media", "tab", "timer", "night_light", "keyboard_light", "windows", "find",
              "dice", "gpu", "lock", "suspend", "mode", "status", "language"}


def maybe_action(text):
    """Cheap test: could this message be asking the PC to do something?"""
    return bool(_ACTION_WORDS.search(_norm(text)))


class ToolFilter:
    """Sits between the model and the screen: passes the text on, keeps [[tool {...}]] calls apart, runs them at the end."""

    def __init__(self, on_text):
        self.on_text, self.buf, self.calls, self.said = self._say_to(on_text), "", [], False

    def _say_to(self, on_text):
        def out(text):
            self.said = self.said or bool(text.strip())
            on_text(text)
        return out

    def feed(self, delta):
        self.buf += delta
        while True:
            i = self.buf.find("[[")
            if i < 0:
                keep = 1 if self.buf.endswith("[") else 0  # a lone "[" may be the start of "[["
                cut = len(self.buf) - keep
                if cut:
                    self.on_text(self.buf[:cut])
                self.buf = self.buf[cut:]
                return
            if i:
                self.on_text(self.buf[:i])
                self.buf = self.buf[i:]
            j = self.buf.find("]]")
            if j < 0:
                return  # the call is still arriving
            m = _CALL.match(self.buf[:j + 2])
            if m and m.group(1) in TOOL_NAMES:
                try:
                    self.calls.append((m.group(1), json.loads(m.group(2) or "{}")))
                except ValueError:
                    pass
                self.buf = self.buf[j + 2:].lstrip(" \t")
            else:
                self.on_text(self.buf[:j + 2])
                self.buf = self.buf[j + 2:]

    def finish(self, lang):
        """The end of the answer: whatever text is left, then the calls are made. Returns the sentence about what was done ('' if nothing)."""
        if self.buf:
            self.on_text(self.buf)
            self.buf = ""
        return execute(self.calls, lang) if self.calls else ""


# ------------------------------------------------------------------------------------------------ doing and telling
SAY = {
    "volume": ("Volume {volume}%.", "Volumen al {volume}%.", "Volume al {volume}%."),
    "volume_muted": ("Sound muted.", "Sonido silenciado.", "Audio disattivato."),
    "brightness": ("Brightness {brightness}%.", "Brillo al {brightness}%.", "Luminosità al {brightness}%."),
    "zoom": ("Zoom {zoom}%.", "Zoom al {zoom}%.", "Zoom al {zoom}%."),
    "zoom_plain": ("Zoom changed.", "Zoom cambiado.", "Zoom cambiato."),
    "timer": ("Timer set for {minutes} minutes.", "Temporizador de {minutes} minutos.", "Timer di {minutes} minuti avviato."),
    "timer_cancel": ("Timer cancelled.", "Temporizador cancelado.", "Timer annullato."),
    "night_on": ("Night light on.", "Luz nocturna encendida.", "Luce notturna accesa."),
    "night_off": ("Night light off.", "Luz nocturna apagada.", "Luce notturna spenta."),
    "dice": ("You rolled a {result}.", "Ha salido un {result}.", "È uscito {result}."),
    "gpu": ("Apps now use {gpu}.", "Las apps usan ahora {gpu}.", "Le app ora usano {gpu}."),
    "suspend": ("Going to sleep in 3 seconds.", "Me suspendo en 3 segundos.", "Sospendo il PC tra 3 secondi."),
    "lock": ("Screen locked.", "Pantalla bloqueada.", "Schermo bloccato."),
    "mode": ("Dial mode: {dial_mode}.", "Modo de la rueda: {dial_mode}.", "Modalità della rotella: {dial_mode}."),
    "status": ("Volume {volume}%, brightness {brightness}%.", "Volumen {volume}%, brillo {brightness}%.", "Volume {volume}%, luminosità {brightness}%."),
    "done": ("Done.", "Hecho.", "Fatto."),
    "no_dial": ("The dial driver is not running, so I cannot do that now.", "El controlador del dial no está activo, no puedo hacerlo ahora.",
                "Il driver del dial non è attivo, ora non posso farlo."),
    "failed": ("I could not do that: {error}.", "No he podido hacerlo: {error}.", "Non ci sono riuscito: {error}."),
}
LANG_INDEX = {"en": 0, "es": 1, "it": 2}


def _say(key, lang, **kw):
    return SAY[key][LANG_INDEX.get(lang, 0)].format(**kw)


def _sentence(name, res, lang):
    if name == "volume":
        return _say("volume_muted", lang) if res.get("muted") else _say("volume", lang, **res)
    if name == "zoom":
        return _say("zoom", lang, **res) if res.get("zoom") else _say("zoom_plain", lang)
    if name == "timer":
        return _say("timer", lang, **res) if "minutes" in res else _say("timer_cancel", lang)
    if name == "night_light":
        return _say("night_on" if res.get("night_light") else "night_off", lang)
    if name in ("brightness", "dice", "gpu", "lock", "suspend", "mode", "status"):
        try:
            return _say(name, lang, **res)
        except KeyError:
            pass
    return _say("done", lang)


def execute(calls, lang="en"):
    """Runs [(tool, args)] on the dial. Returns the sentence to show (and speak) about the results."""
    parts = []
    for name, args in calls:
        if not isinstance(args, dict):
            continue
        res = call(name, **args)
        if res.get("ok"):
            parts.append(_sentence(name, res, lang))
        elif res.get("error") == "dial":
            return _say("no_dial", lang)
        else:
            parts.append(_say("failed", lang, error=res.get("error", "?")))
    return " ".join(parts)


# ------------------------------------------------------------------------------------------------ understanding commands
def _norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


_UNITS = {"zero": 0, "due": 2, "tre": 3, "quattro": 4, "cinque": 5, "sei": 6, "sette": 7, "otto": 8, "nove": 9,
          "dieci": 10, "undici": 11, "dodici": 12, "tredici": 13, "quattordici": 14, "quindici": 15, "sedici": 16, "diciassette": 17,
          "diciotto": 18, "diciannove": 19, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
          "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
          "seventeen": 17, "eighteen": 18, "nineteen": 19, "dos": 2, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
          "nueve": 9, "diez": 10, "doce": 12, "trece": 13, "catorce": 14, "quince": 15}
_TENS = {"venti": 20, "trenta": 30, "quaranta": 40, "cinquanta": 50, "sessanta": 60, "settanta": 70, "ottanta": 80, "novanta": 90,
         "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
         "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90}
_WORDNUM = dict(_UNITS)
for _w, _n in _TENS.items():
    _WORDNUM[_w] = _n
    for _u, _k in ((u, k) for u, k in {**_UNITS, "uno": 1, "one": 1, "un": 1}.items() if 1 <= k <= 9):
        for _form in (_w + _u, _w[:-1] + _u, _w + " " + _u, _w + "-" + _u, _w + " y " + _u):  # trentatre, ventuno, fifty five, treinta y cinco
            _WORDNUM[_form] = _n + _k
_WORDNUM.update({"cento": 100, "cien": 100, "ciento": 100, "hundred": 100})
_NUMBER_WORDS = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(_WORDNUM, key=len, reverse=True)) + r")\b")


def _numbers_as_digits(t):
    return _NUMBER_WORDS.sub(lambda m: str(_WORDNUM[m.group(1)]), t)


_NUM = r"(\d+(?:[.,]\d+)?)"
_UP = r"\b(alza\w*|aument\w*|piu|sali\w*|incremen\w*|raise|increase|up|higher|brighter|louder|sube\w*|mas|amplia\w*)\b"
_DOWN = r"\b(abbass\w*|dimin\w*|ridu\w*|meno|scend\w*|giu|lower|decrease|reduce|down|dim|quieter|baja\w*|disminuy\w*|menos)\b"
_SEPARATORS = re.compile(r"\s*(?:,(?!\d)|;|\.\s|\be\b|\bed\b|\bpoi\b|\band\b|\bthen\b|\by\b|\bluego\b|\banche\b|\balso\b|\btambien\b)\s*")
_QUESTION = re.compile(r"^\s*(come|how|perche|why|cosa|che cos|what|qual|which|chi |who|que es|como|por que|puoi spiegare|explain)\b")


def _n(m):
    return float(m.group(1).replace(",", "."))


def _level_change(c, direction, name, step_default=15):
    """volume / brightness: 'a 30', 'di 20', 'al massimo', or just up/down. Returns the args for the tool (None: nothing to do)."""
    if re.search(r"\b(al massimo|massimo|massima|max|maximum|full|al maximo|maximo)\b", c):
        return {"mode": "set", "value": 100}
    if re.search(r"\b(al minimo|minimo|minima|minimum|lowest)\b", c):
        return {"mode": "set", "value": 5 if name == "brightness" else 0}
    num = re.search(_NUM, c)
    if num:
        v = _n(num)
        rel = re.search(r"\b(del|dello|della|di|by|de|of)\s+(un\s+)?" + re.escape(num.group(1)), c)
        if rel and direction:
            return {"mode": direction, "value": v}
        return {"mode": "set", "value": v}
    if re.search(r"\b(molto|tanto|a lot|much|mucho)\b", c):
        step_default = 30
    return {"mode": direction, "value": step_default} if direction else None


def _parse_clause(c, last_dir):
    """One piece of the sentence -> (list of (tool, args), the direction to carry to the next piece)."""
    own = "up" if re.search(_UP, c) else "down" if re.search(_DOWN, c) else None
    inherited = own or last_dir  # "abbassa la luminosità e il volume": the second piece has no verb of its own
    out = []
    num = re.search(_NUM, c)
    if re.search(r"\b(luminosita|brightness|brillo|luce dello schermo)\b", c):
        a = _level_change(c, inherited, "brightness")
        if a:
            out.append(("brightness", a))
    if re.search(r"\b(volume|volumen)\b", c) or (re.search(r"\b(audio|sound|sonido|suono)\b", c) and not re.search(r"\b(mut\w*|silenz\w*|silenc\w*)\b", c)):
        a = _level_change(c, inherited, "volume")
        if a:
            out.append(("volume", a))
    elif re.search(r"\b(riattiva l audio|unmute|reactiva el sonido)\b", c):
        out.append(("volume", {"mode": "unmute"}))
    elif re.search(r"\b(mut[eo]|silenz\w*|silenci\w*|togli l audio|zitto)\b", c):
        out.append(("volume", {"mode": "mute"}))
    if re.search(r"\b(zoom\w*|ingrandisc\w*|ingrandire|rimpicciolisc\w*|rimpicciolire|ingrandimento|agranda\w*|acerca\w*|aleja\w*)\b", c):
        shrink = own == "down" or re.search(r"\b(rimpicciolisc\w*|rimpicciolire|zoom out|aleja\w*)\b", c)
        if re.search(r"\b(reset\w*|normale|ripristin\w*|originale|default|restablece\w*)\b", c):
            out.append(("zoom", {"mode": "reset"}))
        elif num:
            v = _n(num)
            if re.search(r"\b(al|a|allo|to|at|hasta|en)\s+" + re.escape(num.group(1)), c):
                out.append(("zoom", {"percent": v}))
            else:  # "zoom del 50%": 50% more (or less)
                out.append(("zoom", {"percent": 100 - v if shrink else 100 + v}))
        else:
            out.append(("zoom", {"mode": "out" if shrink else "in"}))
    if re.search(r"\b(scorri\w*|scroll\w*|desplaza\w*)\b", c):
        up = re.search(r"\b(su|up|arriba|sopra)\b", c) or own == "up"
        out.append(("scroll", {"direction": "up" if up else "down", "amount": int(_n(num)) if num else 5}))
    if re.search(r"\b(pausa|pause|metti in pausa)\b", c):
        out.append(("media", {"action": "pause"}))
    elif re.search(r"\b(play|riproduci|riprendi|resume|reproduce)\b", c):
        out.append(("media", {"action": "play"}))
    track = r"(traccia|canzone|brano|song|track|cancion)"
    if re.search(r"\b(prossim\w+|successiv\w+|next|siguiente)\b.*\b" + track + r"\b|\b" + track + r"\b.*\b(prossim\w+|successiv\w+|next|siguiente)\b", c):
        out.append(("media", {"action": "next"}))
    elif re.search(r"\b(precedent\w+|previous|anterior)\b.*\b" + track + r"\b|\b" + track + r"\b.*\b(precedent\w+|previous|anterior)\b", c):
        out.append(("media", {"action": "previous"}))
    if re.search(r"\b(schede|scheda|tab|tabs|pestana\w*)\b", c):
        act = ("new" if re.search(r"\b(nuov\w+|new|nueva)\b", c) else "close" if re.search(r"\b(chiud\w+|close|cierra\w*)\b", c) else
               "reopen" if re.search(r"\b(riapri\w*|reopen|reabre\w*)\b", c) else
               "previous" if re.search(r"\b(precedent\w+|previous|anterior|indietro|back)\b", c) else
               "next" if re.search(r"\b(success\w+|prossim\w+|next|siguiente|avanti)\b", c) else None)
        if act:
            out.append(("tab", {"action": act}))
    if re.search(r"\b(timer|temporizador|conto alla rovescia|countdown|cuenta atras|svegliami|wake me|despiertame)\b", c):
        if re.search(r"\b(annull\w+|cancel\w*|stop|ferma\w*|elimina|disattiva|cancela\w*)\b", c):
            out.append(("timer", {"cancel": True}))
        elif num:
            v = _n(num)
            if re.search(r"\b(or[ae]|hours?|horas?)\b", c):
                v *= 60
            elif re.search(r"\b(second\w*|secondi|segundos?)\b", c):
                v = max(1, v / 60)
            out.append(("timer", {"minutes": round(v)}))
    if re.search(r"\b(luce notturna|night light|nightlight|modalita notte|luz nocturna|filtro (della )?luce blu|blue light)\b", c):
        off = re.search(r"\b(spegn\w+|disattiv\w+|off|disable|apaga\w*|desactiv\w*|togli)\b", c)
        out.append(("night_light", {"state": "off" if off else "on"}))
    if re.search(r"\b(retroilluminazione|luce della tastiera|tastiera illuminata|keyboard (light|backlight)|luz del teclado)\b", c):
        off = re.search(r"\b(spegn\w+|disattiv\w+|off|apaga\w*|togli)\b", c)
        if num and not off:
            out.append(("keyboard_light", {"level": int(_n(num))}))
        else:
            out.append(("keyboard_light", {"state": "off" if off else "on"}))
    if re.search(r"\b(blocca|bloccare|lock|bloquea\w*)\b.*\b(schermo|pc|computer|screen|sessione|pantalla|ordenador)\b", c):
        out.append(("lock", {}))
    if re.search(r"\b(sospendi\w*|sospensione|stand ?by|suspend\w*|suspende\w*|metti a dormire|put (the )?(pc|computer) to sleep|go to sleep)\b", c):
        out.append(("suspend", {}))
    if re.search(r"\b(dado|dice|die|dados?)\b", c) and re.search(r"\b(tira\w*|lancia\w*|roll\w*|throw|lanza\w*)\b", c):
        sides = re.search(r"\b(\d+) (?:facce|lati|sides|caras)\b|\bd(\d+)\b", c)
        out.append(("dice", {"sides": int(next(g for g in sides.groups() if g)) if sides else 6}))
    if re.search(r"\b(cambia|switch|alterna|passa)\b.*\b(finestra|window|app|ventana)\b", c):
        out.append(("windows", {"action": "switch"}))
    if re.search(r"\b(scheda video|gpu|grafica)\b", c):
        if re.search(r"\b(integrat\w+|integrated|integrada|amd|radeon)\b", c):
            out.append(("gpu", {"which": "integrated"}))
        elif re.search(r"\b(dedicat\w+|discrete|dedicada|nvidia|rtx|potente)\b", c):
            out.append(("gpu", {"which": "dedicated"}))
    return out, inherited


def quick(text):
    """The commands in a sentence -> [(tool, args)], or None when it is not (only) a command. Local and instant."""
    t = _numbers_as_digits(_norm(text.strip()))
    if not t or len(t) > 160 or _QUESTION.search(t) or t.endswith("?"):
        return None
    calls, last_dir = [], None
    for clause in (p.strip() for p in _SEPARATORS.split(t + " ") if p and p.strip()):
        found, last_dir = _parse_clause(clause, last_dir)
        calls += found
    return calls or None

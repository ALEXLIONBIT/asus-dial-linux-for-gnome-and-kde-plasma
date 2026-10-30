"""ASUS Dial AI: everything that is not drawing. Config, chats, translations, the automatic installer
(Ollama, a private Python venv with AirLLM / Whisper / Piper), the model engines and the voice back end.

No GTK in here: the UI hands over a small `ui` object (see Engine) and gets called back from worker threads.
"""
import array
import hashlib
import json
import math
import os
import queue
import re
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
import wave

import asus_dial_ai_tools as tools

HOME = os.path.expanduser("~/.local/share/asus-dial-ai")
CONFIG = os.path.expanduser("~/.config/asus-dial/ai-app.json")
CHATS = os.path.join(HOME, "chats")
VENV = os.path.join(HOME, "venv")
LOGFILE = os.path.expanduser("~/.cache/asus-dial-ai.log")
LANG_FILE = os.path.expanduser("~/.config/asus-dial.lang")
WORKER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "asus_dial_ai_worker.py")
if not os.path.exists(WORKER):
    WORKER = os.path.expanduser("~/.local/bin/asus_dial_ai_worker.py")
OLLAMA_HOME = os.path.expanduser("~/.local/ollama")
OLLAMA_URL = "https://github.com/ollama/ollama/releases/latest/download"
OLLAMA_API = "http://127.0.0.1:11434"
UV_URL = "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz"

# ---------------------------------------------------------------------------------------------- the models
# id is what the dial passes (low / mid / high / max); `color` is the colour of its name everywhere.
MODELS = [
    dict(id="low", backend="ollama", name="MiniCPM5-2B", tag="openbmb/minicpm5-2b", size="1.6 GB", color="#3ddc84"),
    dict(id="mid", backend="ollama", name="Llama 3.1 8B", tag="llama3.1:8b", size="4.9 GB", color="#ffc233"),
    dict(id="high", backend="ollama", name="DeepSeek-R1-Distill-Qwen-14B", tag="deepseek-r1:14b", size="9 GB", color="#ff5a4d"),
    dict(id="max", backend="airllm", name="Llama 3.3 70B", hf="unsloth/Llama-3.3-70B-Instruct", size="~140 GB",
         color="rainbow", download_gb=141, layers_gb=40),
    dict(id="custom", backend="ollama", name="Custom", tag="", size="?", color="#38bdf8"),  # any Ollama model, see set_custom_model
]
MODEL_IDS = [m["id"] for m in MODELS]
LEVEL_NAMES = {"en": ("Low", "Medium", "High", "MAX", "Custom"), "es": ("Bajo", "Medio", "Alto", "MAX", "Propio"),
               "it": ("Basso", "Medio", "Alto", "MAX", "Custom")}
VOICE_FOR = {"en": "en_US-lessac-medium", "es": "es_ES-davefx-medium", "it": "it_IT-paola-medium"}
# Ten voice presets. Each picks a Piper voice per language and a character: speed, pitch (1 = normal), volume,
# expressiveness ("var", 1 = normal) and an effect. All of it can be tuned afterwards in the settings.
VOICE_PRESETS = {
    "aurora":   dict(v=dict(en="en_US-amy-medium", it="it_IT-serena-medium", es="es_MX-claude-high"), speed=1.0, pitch=1.0, volume=1.0, var=1.0, fx="none"),
    "marco":    dict(v=dict(en="en_US-ryan-high", it="it_IT-riccardo-x_low", es="es_ES-davefx-medium"), speed=1.0, pitch=1.0, volume=1.0, var=1.0, fx="none"),
    "nova":     dict(v=dict(en="en_US-kristin-medium", it="it_IT-paola-medium", es="es_MX-claude-high"), speed=1.18, pitch=1.06, volume=1.0, var=1.2, fx="none"),
    "atlas":    dict(v=dict(en="en_US-john-medium", it="it_IT-riccardo-x_low", es="es_MX-ald-medium"), speed=0.9, pitch=0.86, volume=1.0, var=0.9, fx="none"),
    "pixel":    dict(v=dict(en="en_US-amy-medium", it="it_IT-paola-medium", es="es_MX-claude-high"), speed=1.15, pitch=1.45, volume=1.0, var=1.2, fx="none"),
    "robo":     dict(v=dict(en="en_US-lessac-medium", it="it_IT-paola-medium", es="es_ES-davefx-medium"), speed=1.0, pitch=0.95, volume=1.0, var=0.5, fx="robot"),
    "whisper":  dict(v=dict(en="en_US-hfc_female-medium", it="it_IT-serena-medium", es="es_ES-sharvard-medium"), speed=0.85, pitch=1.0, volume=0.6, var=0.4, fx="none"),
    "narrator": dict(v=dict(en="en_US-joe-medium", it="it_IT-serena-medium", es="es_ES-sharvard-medium"), speed=0.93, pitch=0.95, volume=1.0, var=1.4, fx="none"),
    "giant":    dict(v=dict(en="en_US-norman-medium", it="it_IT-riccardo-x_low", es="es_MX-ald-medium"), speed=0.82, pitch=0.68, volume=1.1, var=1.0, fx="none"),
    "echo":     dict(v=dict(en="en_US-hfc_male-medium", it="it_IT-paola-medium", es="es_MX-claude-high"), speed=1.0, pitch=1.0, volume=1.0, var=1.0, fx="echo"),
}


def preset_values(pid):
    p = VOICE_PRESETS[pid]
    return dict(voice_speed=p["speed"], voice_pitch=p["pitch"], voice_volume=p["volume"], voice_var=p["var"], voice_fx=p["fx"])


def model_by_id(mid):
    return next((m for m in MODELS if m["id"] == mid), MODELS[0])


def set_custom_model(tag):
    """The Ollama name of the custom model: "qwen3:8b", "user/model", "hf.co/user/repo:Q4_K_M"..."""
    m = model_by_id("custom")
    m["tag"] = tag.strip()
    m["name"] = m["tag"] or "Custom"


# ---------------------------------------------------------------------------------------------- languages
def read_lang():
    try:
        v = open(LANG_FILE).read().strip()
        return v if v in ("es", "it") else "en"
    except OSError:
        return "en"


LANG = [read_lang()]

STR = {
    "app": ("ASUS Dial AI", "ASUS Dial IA", "ASUS Dial AI"),
    "new_chat": ("New chat", "Nuevo chat", "Nuova chat"),
    "search": ("Search chats", "Buscar chats", "Cerca chat"),
    "placeholder": ("Message ASUS Dial AI…", "Escribe a ASUS Dial IA…", "Scrivi ad ASUS Dial AI…"),
    "hello": ("How can I help you?", "¿En qué puedo ayudarte?", "Come posso aiutarti?"),
    "sug1": ("Explain quantum computing simply", "Explícame la computación cuántica fácil",
             "Spiegami il calcolo quantistico in modo semplice"),
    "sug2": ("Write a short poem about the sea", "Escribe un poema corto sobre el mar",
             "Scrivi una breve poesia sul mare"),
    "sug3": ("Give me 5 ideas for a weekend project", "Dame 5 ideas para un proyecto de fin de semana",
             "Dammi 5 idee per un progetto del weekend"),
    "thinking": ("Thinking…", "Pensando…", "Sto pensando…"),
    "thought": ("Reasoning", "Razonamiento", "Ragionamento"),
    "listening": ("Listening…", "Escuchando…", "Ti ascolto…"),
    "speaking": ("Speaking…", "Hablando…", "Parlo…"),
    "voice_loading": ("Preparing voice…", "Preparando la voz…", "Preparo la voce…"),
    "voice_hint": ("Just talk. Click the orb to interrupt.", "Habla. Haz clic en la esfera para interrumpir.",
                   "Parla pure. Clicca la sfera per interrompere."),
    "mic_muted": ("Microphone off: click it to talk again", "Micrófono apagado: haz clic para volver a hablar",
                  "Microfono spento: cliccalo per tornare a parlare"),
    "voice_mic_tip": ("Microphone on / off", "Micrófono encendido / apagado", "Microfono acceso / spento"),
    "voice_spk_tip": ("Voice on / off (answers stay as text)", "Voz encendida / apagada (las respuestas quedan en texto)",
                      "Voce accesa / spenta (le risposte restano scritte)"),
    "voice_off": ("Close voice mode", "Cerrar modo voz", "Chiudi la modalità vocale"),
    "mic": ("Voice mode", "Modo voz", "Modalità vocale"),
    "send": ("Send", "Enviar", "Invia"),
    "stop": ("Stop", "Detener", "Ferma"),
    "settings": ("Settings", "Ajustes", "Impostazioni"),
    "delete": ("Delete", "Borrar", "Elimina"),
    "rename": ("Rename", "Renombrar", "Rinomina"),
    "copy": ("Copy", "Copiar", "Copia"),
    "read": ("Read aloud", "Leer en voz alta", "Leggi ad alta voce"),
    "cancel": ("Cancel", "Cancelar", "Annulla"),
    "install": ("Install and download", "Instalar y descargar", "Installa e scarica"),
    "need_title": ("{name} needs to be set up", "{name} necesita prepararse", "{name} va preparato"),
    "need_intro": ("This is done once, then it just works:", "Se hace una sola vez, luego funciona solo:",
                   "Si fa una volta sola, poi funziona e basta:"),
    "need_ollama": ("• Ollama, the local model runner (~1.4 GB, installed only for you, no sudo)",
                    "• Ollama, el ejecutor de modelos local (~1,4 GB, solo para tu usuario, sin sudo)",
                    "• Ollama, il programma che esegue i modelli in locale (~1,4 GB, solo per te, senza sudo)"),
    "custom_title": ("Custom model", "Modelo propio", "Modello custom"),
    "custom_text": ("Write the name of any Ollama model (qwen3:8b, gemma3:4b, hf.co/user/repo:Q4_K_M) or pick one you already have. "
                    "If it is missing it is downloaded the first time you use it.",
                    "Escribe el nombre de cualquier modelo de Ollama (qwen3:8b, gemma3:4b, hf.co/usuario/repo:Q4_K_M) o elige uno que ya tengas. "
                    "Si falta, se descarga la primera vez que lo uses.",
                    "Scrivi il nome di un qualsiasi modello di Ollama (qwen3:8b, gemma3:4b, hf.co/utente/repo:Q4_K_M) o scegline uno che hai già. "
                    "Se manca, viene scaricato la prima volta che lo usi."),
    "custom_none": ("No custom model chosen yet", "Todavía no has elegido un modelo propio", "Nessun modello custom scelto"),
    "custom_ok": ("Use this model", "Usar este modelo", "Usa questo modello"),
    "need_model": ("• The model {name} ({size})", "• El modelo {name} ({size})", "• Il modello {name} ({size})"),
    "need_env": ("• A private Python with AirLLM and PyTorch (~5 GB)",
                 "• Un Python privado con AirLLM y PyTorch (~5 GB)", "• Un Python privato con AirLLM e PyTorch (~5 GB)"),
    "need_voice": ("• Speech recognition and voice (~1 GB)", "• Reconocimiento de voz y voz (~1 GB)",
                   "• Riconoscimento vocale e voce (~1 GB)"),
    "need_max_model": ("• {name} from Hugging Face ({size}), converted layer by layer (~{layers} GB more)",
                       "• {name} de Hugging Face ({size}), convertido capa por capa (~{layers} GB más)",
                       "• {name} da Hugging Face ({size}), convertito strato per strato (~{layers} GB in più)"),
    "need_slow": ("MAX is VERY slow: it streams a 70B model through a small GPU, expect minutes per sentence.",
                  "MAX es MUY lento: pasa un modelo de 70B por una GPU pequeña, espera minutos por frase.",
                  "MAX è MOLTO lento: fa passare un modello da 70B in una GPU piccola, aspettati minuti a frase."),
    "no_space": ("Not enough free disk space: {need} GB needed, {have} GB free.",
                 "No hay espacio en disco: hacen falta {need} GB, hay {have} GB libres.",
                 "Spazio su disco insufficiente: servono {need} GB, ce ne sono {have} liberi."),
    "step_uv": ("Getting the installer (uv)…", "Descargando el instalador (uv)…", "Scarico l'installer (uv)…"),
    "step_venv": ("Creating a private Python…", "Creando un Python privado…", "Creo un Python privato…"),
    "step_pkgs": ("Installing packages…", "Instalando paquetes…", "Installo i pacchetti…"),
    "step_ollama": ("Downloading Ollama…", "Descargando Ollama…", "Scarico Ollama…"),
    "step_server": ("Starting Ollama…", "Iniciando Ollama…", "Avvio Ollama…"),
    "step_pull": ("Downloading {name}…", "Descargando {name}…", "Scarico {name}…"),
    "step_load": ("Loading {name}…", "Cargando {name}…", "Carico {name}…"),
    "step_download": ("Downloading {name}", "Descargando {name}", "Scarico {name}"),
    "step_split": ("Converting {name} layer by layer (one time only, this takes a long while)…",
                   "Convirtiendo {name} capa por capa (solo una vez, tarda mucho)…",
                   "Converto {name} strato per strato (una volta sola, ci vuole molto)…"),
    "step_stt": ("Loading speech recognition…", "Cargando el reconocimiento de voz…", "Carico il riconoscimento vocale…"),
    "step_voice": ("Downloading the voice…", "Descargando la voz…", "Scarico la voce…"),
    "checksum_bad": ("The checksum does not match: download discarded.",
                     "La suma de comprobación no coincide: descarga descartada.",
                     "Il checksum non coincide: download scartato."),
    "mic_loud": ("The microphone is saturated: lower its input volume in the system sound settings",
                 "El micrófono está saturado: baja su volumen de entrada en los ajustes de sonido",
                 "Il microfono è saturo: abbassa il volume di ingresso nelle impostazioni audio"),
    "sink_muted": ("The sound output is muted or at 0%: raise the volume to hear the voice",
                   "La salida de sonido está silenciada o al 0 %: sube el volumen para oír la voz",
                   "L'uscita audio è muta o a 0%: alza il volume per sentire la voce"),
    "speak_on": ("Answers will be read aloud", "Las respuestas se leerán en voz alta", "Le risposte verranno lette ad alta voce"),
    "speak_off": ("Reading aloud is off", "Lectura en voz alta desactivada", "Lettura ad alta voce disattivata"),
    "error": ("Something went wrong", "Algo salió mal", "Qualcosa è andato storto"),
    "cpu_note": ("No usable GPU: running on the CPU.", "Sin GPU utilizable: se usa la CPU.",
                 "Nessuna GPU utilizzabile: uso la CPU."),
    "copied": ("Copied", "Copiado", "Copiato"),
    "you": ("You", "Tú", "Tu"),
    "details": ("Details", "Detalles", "Dettagli"),
    "now_running": ("Running on {name}", "Usando {name}", "Uso {name}"),
    # settings
    "s_appearance": ("Appearance", "Apariencia", "Aspetto"),
    "s_animations": ("Animations", "Animaciones", "Animazioni"),
    "s_chat": ("Chat", "Chat", "Chat"),
    "s_voice": ("Voice", "Voz", "Voce"),
    "s_max": ("MAX (AirLLM)", "MAX (AirLLM)", "MAX (AirLLM)"),
    "s_theme": ("Theme", "Tema", "Tema"),
    "s_accent": ("Accent colour", "Color de acento", "Colore d'accento"),
    "s_font": ("Text size", "Tamaño del texto", "Dimensione del testo"),
    "s_radius": ("Bubble roundness", "Redondez de las burbujas", "Rotondità delle bolle"),
    "s_bg": ("Background", "Fondo", "Sfondo"),
    "s_orb": ("AI orb", "Esfera de la IA", "Sfera dell'AI"),
    "s_anim_on": ("Animations", "Animaciones", "Animazioni"),
    "s_anim_speed": ("Speed", "Velocidad", "Velocità"),
    "s_msg_anim": ("New messages", "Mensajes nuevos", "Nuovi messaggi"),
    "s_smooth": ("Smooth scrolling", "Desplazamiento suave", "Scorrimento fluido"),
    "s_system": ("System prompt (how the AI behaves)", "Instrucciones del sistema (cómo se comporta la IA)",
                 "Istruzioni di sistema (come si comporta l'AI)"),
    "s_temp": ("Creativity", "Creatividad", "Creatività"),
    "s_tokens": ("Max answer length", "Longitud máxima de respuesta", "Lunghezza massima della risposta"),
    "s_tokens_max": ("Max answer length for MAX", "Longitud máxima para MAX", "Lunghezza massima per MAX"),
    "s_think": ("Show the reasoning", "Mostrar el razonamiento", "Mostra il ragionamento"),
    "s_enter": ("Enter sends (Shift+Enter = new line)", "Intro envía (Mayús+Intro = nueva línea)",
                "Invio manda (Maiusc+Invio = a capo)"),
    "s_tts": ("Speak the answers in voice mode", "Leer las respuestas en modo voz", "Leggi le risposte in modalità vocale"),
    "s_vlang": ("Speech language", "Idioma de la voz", "Lingua del parlato"),
    "s_preset": ("Voice", "Voz", "Voce"),
    "s_vspeed": ("Speed", "Velocidad", "Velocità"),
    "s_vpitch": ("Pitch", "Tono", "Tono"),
    "s_vvol": ("Volume", "Volumen", "Volume"),
    "s_vvar": ("Expressiveness", "Expresividad", "Espressività"),
    "s_vfx": ("Effect", "Efecto", "Effetto"),
    "s_test": ("Test the voice", "Probar la voz", "Prova la voce"),
    "s_tools": ("The AI can control the PC (volume, brightness, zoom, tabs, timer...)", "La IA puede controlar el PC (volumen, brillo, zoom, pestañas, temporizador...)",
                "L'AI può controllare il PC (volume, luminosità, zoom, schede, timer...)"),
    "s_autospeak": ("Read answers aloud in the normal chat too", "Leer las respuestas también en el chat normal",
                    "Leggi le risposte ad alta voce anche nella chat normale"),
    "test_text": ("Hi! This is how I sound.", "¡Hola! Así es como sueno.", "Ciao! Ecco come suono."),
    "fx_none": ("None", "Ninguno", "Nessuno"), "fx_robot": ("Robot", "Robot", "Robot"), "fx_echo": ("Echo", "Eco", "Eco"),
    "p_aurora": ("Aurora · calm and warm", "Aurora · calma y cálida", "Aurora · calma e calda"),
    "p_marco": ("Marco · friendly man", "Marco · hombre amable", "Marco · voce maschile amichevole"),
    "p_nova": ("Nova · bright and quick", "Nova · alegre y rápida", "Nova · vivace e veloce"),
    "p_atlas": ("Atlas · deep and slow", "Atlas · grave y lento", "Atlas · profonda e lenta"),
    "p_pixel": ("Pixel · chipmunk", "Pixel · ardilla", "Pixel · scoiattolo"),
    "p_robo": ("Robo · robot", "Robo · robot", "Robo · robot"),
    "p_whisper": ("Whisper · soft and slow", "Whisper · suave y lento", "Whisper · sussurrata"),
    "p_narrator": ("Narrator · storyteller", "Narrador · cuentacuentos", "Narratore · cantastorie"),
    "p_giant": ("Giant · huge", "Gigante · enorme", "Gigante · enorme"),
    "p_echo": ("Echo · spacey", "Eco · espacial", "Eco · spaziale"),
    "speak_tip": ("Read answers aloud", "Leer respuestas en voz alta", "Leggi le risposte ad alta voce"),
    "voice_nothink": ("Reasoning is off in voice mode, for faster answers.", "El razonamiento está desactivado en modo voz para responder antes.",
                      "Il ragionamento è disattivato in modalità vocale, per rispondere prima."),
    "s_stt": ("Recognition quality", "Calidad del reconocimiento", "Qualità del riconoscimento"),
    "s_comp": ("Compression (needs the GPU)", "Compresión (necesita la GPU)", "Compressione (serve la GPU)"),
    "s_delorig": ("Delete the original download after converting (saves ~140 GB)",
                  "Borrar la descarga original tras convertir (ahorra ~140 GB)",
                  "Cancella il download originale dopo la conversione (risparmia ~140 GB)"),
    "s_auto": ("Automatic", "Automático", "Automatico"),
    "s_none": ("None", "Ninguno", "Nessuno"),
    "s_fade": ("Fade", "Desvanecer", "Dissolvenza"),
    "s_slide": ("Slide", "Deslizar", "Scorri"),
    "s_pop": ("Pop", "Pop", "Pop"),
    "s_aurora": ("Aurora", "Aurora", "Aurora"),
    "s_plain": ("Plain", "Liso", "Semplice"),
    "s_blob": ("Liquid", "Líquido", "Liquida"),
    "s_rings": ("Rings", "Anillos", "Anelli"),
    "s_spark": ("Sparkle", "Destellos", "Scintille"),
    "t_midnight": ("Midnight", "Medianoche", "Mezzanotte"),
    "t_oled": ("OLED black", "Negro OLED", "Nero OLED"),
    "t_light": ("Light", "Claro", "Chiaro"),
    "t_sunset": ("Sunset", "Atardecer", "Tramonto"),
    "t_ocean": ("Ocean", "Océano", "Oceano"),
    "t_forest": ("Forest", "Bosque", "Foresta"),
}


def T(key, **kw):
    row = STR.get(key)
    if not row:
        return key
    s = row[("en", "es", "it").index(LANG[0])]
    return s.format(**kw) if kw else s


# ---------------------------------------------------------------------------------------------- config
DEFAULTS = dict(
    model="low", theme="midnight", accent="#7c5cff", font_size=14, radius=18, background="aurora", orb="blob",
    animations=True, anim_speed=1.0, msg_anim="slide", smooth_scroll=True,
    system_prompt="", temperature=0.7, max_tokens=1024, max_tokens_max=192, show_thinking=True, enter_sends=True,
    tts=True, auto_speak=False, voice_lang="auto", stt_size="small", voice_preset="aurora", voice_speed=1.0, voice_pitch=1.0,
    voice_volume=1.0, voice_var=1.0, voice_fx="none", compression="4bit", delete_original=True,
    sidebar=True, win_w=1100, win_h=760, dial_tools=True, custom_model="",
)


class Config:
    def __init__(self):
        self.data = dict(DEFAULTS)
        self.listeners = []
        try:
            with open(CONFIG) as f:
                self.data.update({k: v for k, v in json.load(f).items() if k in DEFAULTS})
        except (OSError, ValueError):
            pass

    def __getitem__(self, k):
        return self.data[k]

    def set(self, k, v):
        if self.data.get(k) == v:
            return
        self.data[k] = v
        self.save()
        for f in self.listeners:
            f(k)

    def save(self):
        try:
            os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
            tmp = CONFIG + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.data, f, indent=1)
            os.replace(tmp, CONFIG)
        except OSError:
            pass


# ---------------------------------------------------------------------------------------------- chats
class ChatStore:
    def __init__(self):
        os.makedirs(CHATS, exist_ok=True)

    def path(self, cid):
        return os.path.join(CHATS, cid + ".json")

    def new(self):
        return dict(id=uuid.uuid4().hex[:12], title="", created=time.time(), updated=time.time(), messages=[])

    def save(self, chat):
        if not chat["messages"]:
            return
        chat["updated"] = time.time()
        try:
            tmp = self.path(chat["id"]) + ".tmp"
            with open(tmp, "w") as f:
                json.dump(chat, f, ensure_ascii=False)
            os.replace(tmp, self.path(chat["id"]))
        except OSError:
            pass

    def delete(self, cid):
        try:
            os.remove(self.path(cid))
        except OSError:
            pass

    def load(self, cid):
        with open(self.path(cid)) as f:
            return json.load(f)

    def list(self):
        out = []
        for fn in os.listdir(CHATS):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(CHATS, fn)) as f:
                        c = json.load(f)
                    out.append(dict(id=c["id"], title=c.get("title") or "…", updated=c.get("updated", 0)))
                except (OSError, ValueError, KeyError):
                    continue
        return sorted(out, key=lambda c: -c["updated"])


# ---------------------------------------------------------------------------------------------- text helpers
def parse_segments(text):
    """Split a model answer into ("think"|"text"|"code", content, closed) pieces."""
    out = []
    pos = 0
    while pos < len(text):
        i = text.find("<think>", pos)
        if i < 0:
            out += _split_code(text[pos:])
            break
        out += _split_code(text[pos:i])
        j = text.find("</think>", i)
        if j < 0:
            out.append(("think", text[i + 7:], False))
            break
        out.append(("think", text[i + 7:j], True))
        pos = j + 8
    return [s for s in out if s[1].strip() or s[0] == "code"]


def _split_code(text):
    out = []
    parts = text.split("```")
    for n, part in enumerate(parts):
        if n % 2 == 0:
            out.append(("text", part.strip("\n"), True))
        else:
            body = part.split("\n", 1)
            lang, code = (body[0].strip(), body[1]) if len(body) == 2 else ("", body[0])
            out.append(("code", code.rstrip("\n"), n < len(parts) - 1, lang))
    return out


def speakable(text):
    """The plain text of an answer to read aloud: no reasoning, no code, no markdown marks."""
    s = " ".join(p[1] for p in parse_segments(text) if p[0] == "text")
    s = re.sub(r"`+|\*+|#+\s*|_{2,}", "", s)
    s = re.sub(r"[\U0001F000-\U0001FAFF☀-➿]", "", s)
    return re.sub(r"[ \t]+", " ", s).strip()


def sentence_cut(text):
    """Index just after the last finished sentence of text (0 if none)."""
    m = list(re.finditer(r"[.!?…:;]+[\"')\]]?(\s+|$)|\n+", text))
    return m[-1].end() if m and m[-1].end() < len(text) + 1 else 0


# ---------------------------------------------------------------------------------------------- installer
class Cancelled(Exception):
    pass


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
        with open(LOGFILE, "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except OSError:
        pass


def download(url, dest, ui, label, cancel):
    req = urllib.request.Request(url, headers={"User-Agent": "asus-dial-ai"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            if cancel.is_set():
                raise Cancelled()
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
            done += len(b)
            if total:
                ui.progress(f"{label}  {done / 1e9:.2f} / {total / 1e9:.2f} GB", done / total)


def run_logged(cmd, ui, text, cancel, env=None):
    """Run cmd, showing its output lines as details; raises on failure."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
    tail = []
    for line in p.stdout:
        line = line.rstrip()
        tail = (tail + [line])[-40:]
        ui.progress(text, None, line)
        log(line)
        if cancel.is_set():
            p.kill()
            raise Cancelled()
    if p.wait() != 0:
        raise RuntimeError("\n".join(tail[-8:]))


PACKAGES = {
    "max": ["airllm", "torch", "transformers", "accelerate", "bitsandbytes", "sentencepiece", "huggingface_hub", "numpy"],
    "voice": ["faster-whisper", "piper-tts", "numpy"],
}


class Env:
    """A private Python 3.12 (the system one is too new for PyTorch) with the heavy packages, made on demand."""

    @staticmethod
    def uv():
        return shutil.which("uv") or os.path.join(HOME, "bin", "uv")

    @staticmethod
    def python():
        return os.path.join(VENV, "bin", "python")

    @staticmethod
    def has(kind):
        return os.path.exists(os.path.join(HOME, f".pkgs-{kind}")) and os.path.exists(Env.python())

    @staticmethod
    def ensure(kind, ui, cancel):
        if Env.has(kind):
            return
        uv = Env.uv()
        if not os.path.exists(uv):
            ui.progress(T("step_uv"), None)
            tmp = tempfile.mkdtemp(prefix="adai-")
            try:
                tgz = os.path.join(tmp, "uv.tgz")
                download(UV_URL, tgz, ui, T("step_uv"), cancel)
                want = urllib.request.urlopen(UV_URL + ".sha256", timeout=30).read().split()[0].decode()
                if hashlib.sha256(open(tgz, "rb").read()).hexdigest() != want:
                    raise RuntimeError(T("checksum_bad"))
                os.makedirs(os.path.dirname(uv), exist_ok=True)
                with tarfile.open(tgz) as t:
                    for m in t.getmembers():
                        if m.isfile() and os.path.basename(m.name) in ("uv", "uvx"):
                            m.name = os.path.basename(m.name)
                            t.extract(m, os.path.dirname(uv), filter="data")
                os.chmod(uv, 0o755)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        if not os.path.exists(Env.python()):
            run_logged([uv, "venv", "--python", "3.12", VENV], ui, T("step_venv"), cancel)
        run_logged([uv, "pip", "install", "--python", Env.python()] + PACKAGES[kind], ui, T("step_pkgs"), cancel)
        open(os.path.join(HOME, f".pkgs-{kind}"), "w").close()


class JsonWorker:
    """A worker process (asus_dial_ai_worker.py inside the venv) spoken to with JSON lines."""

    def __init__(self, mode, on_log=None):
        os.makedirs(HOME, exist_ok=True)
        self.mode = mode
        self.events = queue.Queue()
        self.p = subprocess.Popen([Env.python(), "-I", WORKER, "--mode", mode], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
                                  env={**os.environ, "PYTHONUNBUFFERED": "1"})
        self.on_log = on_log or (lambda line: None)
        threading.Thread(target=self._read_out, daemon=True).start()
        threading.Thread(target=self._read_err, daemon=True).start()

    def _read_out(self):
        for line in self.p.stdout:
            try:
                self.events.put(json.loads(line))
            except ValueError:
                pass
        self.events.put({"event": "exit"})

    def _read_err(self):
        for line in self.p.stderr:
            line = line.rstrip()
            log(f"[{self.mode}] {line}")
            if line:
                self.on_log(line[-200:])

    def alive(self):
        return self.p.poll() is None

    def send(self, **cmd):
        self.p.stdin.write(json.dumps(cmd, ensure_ascii=False) + "\n")
        self.p.stdin.flush()

    def get(self, cancel=None, timeout=0.3):
        """Next event, or None while waiting; raises Cancelled when cancel is set."""
        while True:
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            try:
                return self.events.get(timeout=timeout)
            except queue.Empty:
                if not self.alive() and self.events.empty():
                    return {"event": "exit"}
                return None

    def close(self):
        try:
            self.send(cmd="quit")
        except (OSError, ValueError):
            pass
        try:
            self.p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.p.kill()


# ---------------------------------------------------------------------------------------------- engines
def http_json(path, body=None, timeout=10):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(OLLAMA_API + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


class Engine:
    """Makes a model ready (installing whatever is missing, asking once) and streams answers from it.

    `ui` must offer (any thread): confirm(title, text, yes_label) -> bool (blocks), progress(text, frac=None, line=None),
    progress_done(), note(text).
    """

    def __init__(self, cfg, ui):
        self.cfg, self.ui = cfg, ui
        self.cancel = threading.Event()  # cancels an install/download
        self.stop = threading.Event()  # stops an answer
        self.air = None
        self.air_ready = False
        self.lock = threading.Lock()

    # ----- ollama
    def ollama_bin(self):
        return shutil.which("ollama") or (os.path.join(OLLAMA_HOME, "bin", "ollama")
                                          if os.path.exists(os.path.join(OLLAMA_HOME, "bin", "ollama")) else None)

    def server_up(self):
        try:
            urllib.request.urlopen(OLLAMA_API + "/", timeout=1).read()
            return True
        except OSError:
            return False

    def installed_models(self):
        """Names of the models Ollama already has ([] while its server is not running)."""
        try:
            return [m["name"] for m in http_json("/api/tags", timeout=1).get("models", []) if m.get("name")]
        except (OSError, ValueError):
            return []

    def ollama_has(self, tag):
        try:
            return any(m.get("name", "").split(":")[0] == tag.split(":")[0] and
                       (":" not in tag or m["name"] == tag) for m in http_json("/api/tags").get("models", []))
        except OSError:
            return False

    def install_ollama(self):
        ui, cancel = self.ui, self.cancel
        tmp = tempfile.mkdtemp(prefix="adai-")
        try:
            tz = os.path.join(tmp, "ollama.tar.zst")
            download(f"{OLLAMA_URL}/ollama-linux-amd64.tar.zst", tz, ui, T("step_ollama"), cancel)
            sums = urllib.request.urlopen(f"{OLLAMA_URL}/sha256sum.txt", timeout=30).read().decode()
            want = next((ln.split()[0] for ln in sums.splitlines() if ln.split()[-1].lstrip("./") == "ollama-linux-amd64.tar.zst"), "")
            h = hashlib.sha256()
            with open(tz, "rb") as f:
                for b in iter(lambda: f.read(1 << 22), b""):
                    h.update(b)
            if not want or h.hexdigest() != want:
                raise RuntimeError(T("checksum_bad"))
            os.makedirs(OLLAMA_HOME, exist_ok=True)
            run_logged(["tar", "--zstd", "-xf", tz, "-C", OLLAMA_HOME], ui, T("step_ollama"), cancel)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def start_server(self):
        if self.server_up():
            return
        self.ui.progress(T("step_server"), None)
        env = {**os.environ, "OLLAMA_FLASH_ATTENTION": "1", "OLLAMA_KV_CACHE_TYPE": "q8_0",
               "OLLAMA_CONTEXT_LENGTH": "4096"}
        os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
        subprocess.Popen([self.ollama_bin(), "serve"], env=env, stdout=open(LOGFILE + ".ollama", "a"),
                         stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(60):
            if self.server_up():
                return
            time.sleep(0.5)
        raise RuntimeError("Ollama did not start (see " + LOGFILE + ".ollama)")

    def pull(self, m):
        text = T("step_pull", name=m["name"])
        req = urllib.request.Request(OLLAMA_API + "/api/pull", data=json.dumps({"model": m["tag"]}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            for line in r:
                if self.cancel.is_set():
                    raise Cancelled()
                d = json.loads(line)
                if d.get("error"):
                    raise RuntimeError(d["error"])
                if d.get("total"):
                    self.ui.progress(f"{text}  {d.get('completed', 0) / 1e9:.2f} / {d['total'] / 1e9:.2f} GB",
                                     d.get("completed", 0) / d["total"])
                else:
                    self.ui.progress(text, None, d.get("status"))

    # ----- ensure
    def needs(self, m):
        """List of (text) things missing for model m."""
        out = []
        if m["backend"] == "ollama":
            if not self.ollama_bin():
                out.append(T("need_ollama"))
            if not (self.ollama_bin() and self.server_up() and self.ollama_has(m["tag"])) and not self._cached_has(m):
                out.append(T("need_model", name=m["name"], size=m["size"]))
        else:
            if not Env.has("max"):
                out.append(T("need_env"))
            if not os.path.exists(self.max_marker()):
                out.append(T("need_max_model", name=m["name"], size=m["size"], layers=m["layers_gb"]))
        return out

    def _cached_has(self, m):
        # server not running: look at the manifest on disk instead of starting it just to ask
        base = os.path.expanduser("~/.ollama/models/manifests")
        if m["id"] == "custom":  # a name the user wrote: only the very same model counts, or it would be downloaded unasked
            name, _, version = m["tag"].partition(":")
            parts = name.split("/")
            if "." not in parts[0]:
                parts = ["registry.ollama.ai"] + (["library"] if len(parts) == 1 else []) + parts
            return os.path.exists(os.path.join(base, *parts, version or "latest"))
        name = m["tag"].split(":")[0]
        return os.path.isdir(base) and any(name.split("/")[-1] in d for _r, ds, _f in os.walk(base) for d in ds) and \
            os.path.exists(os.path.join(base, "registry.ollama.ai"))

    def max_marker(self):
        return os.path.join(HOME, f".max-ready-{self.cfg['compression']}")

    def ensure(self, m):
        """Installs/downloads what model m needs, then loads it. Raises Cancelled or RuntimeError."""
        self.cancel.clear()
        try:
            missing = self.needs(m)
            if missing:
                if m["backend"] == "airllm":
                    free = shutil.disk_usage(HOME if os.path.isdir(HOME) else os.path.expanduser("~")).free / 1e9
                    need = m["download_gb"] + m["layers_gb"] + 8
                    if free < need:
                        raise RuntimeError(T("no_space", need=need, have=round(free)))
                lines = [T("need_intro")] + missing + ([T("need_slow")] if m["backend"] == "airllm" else [])
                if not self.ui.confirm(T("need_title", name=m["name"]), "\n".join(lines), T("install")):
                    raise Cancelled()
            if m["backend"] == "ollama":
                self.stop_air()
                if not self.ollama_bin():
                    self.install_ollama()
                self.start_server()
                if not self.ollama_has(m["tag"]):
                    self.pull(m)
                self.ui.progress(T("step_load", name=m["name"]), None)
                http_json("/api/generate", {"model": m["tag"], "prompt": "", "keep_alive": "30m",
                                            "options": {"num_ctx": 4096}}, timeout=600)
            else:
                self.unload_ollama()
                Env.ensure("max", self.ui, self.cancel)
                self.start_air(m)
        finally:
            self.ui.progress_done()

    def unload_ollama(self):
        try:
            if self.server_up():
                for r in http_json("/api/ps").get("models", []):
                    http_json("/api/generate", {"model": r["name"], "keep_alive": 0})
        except OSError:
            pass

    def stop_air(self):
        if self.air:
            self.air.close()
            self.air, self.air_ready = None, False

    def start_air(self, m):
        if self.air and self.air.alive() and self.air_ready:
            return
        self.stop_air()
        ui = self.ui
        w = JsonWorker("airllm", on_log=lambda line: ui.progress(None, None, line))
        self.air = w
        w.send(cmd="load", model=m["hf"], compression=self.cfg["compression"], delete_original=self.cfg["delete_original"])
        phase = T("step_load", name=m["name"])
        while True:
            e = w.get(self.cancel)
            if e is None:
                continue
            ev = e.get("event")
            if ev == "download":
                phase = T("step_download", name=m["name"])
                ui.progress(f"{phase}  {e['done'] / 1e9:.1f} / {e['total'] / 1e9:.1f} GB", e["done"] / max(1, e["total"]))
            elif ev == "status":
                phase = T("step_split", name=m["name"]) if e.get("key") == "splitting" else T("step_load", name=m["name"])
                ui.progress(phase, None)
            elif ev == "device":
                if e.get("device") == "cpu":
                    ui.note(T("cpu_note"))
            elif ev == "loaded":
                self.air_ready = True
                open(self.max_marker(), "w").close()
                return
            elif ev in ("error", "exit"):
                self.stop_air()
                raise RuntimeError(e.get("msg") or "AirLLM stopped (see " + LOGFILE + ")")

    # ----- chat
    def stream(self, m, messages, on_text, think=True):
        """Streams the answer, calling on_text(delta). Returns when finished or stopped.
        think=False asks the model not to reason first (voice mode wants short, fast answers).
        With the dial tools on, the model may ask for PC actions; they are run here and the answer ends with what was done."""
        self.stop.clear()
        sysmsg = self.cfg["system_prompt"].strip()
        flt = None
        if self.cfg["dial_tools"] and tools.maybe_action(messages[-1]["content"] if messages else ""):  # the long tool list only when it can matter
            sysmsg = (sysmsg + "\n\n" if sysmsg else "") + tools.PROMPT
            flt = tools.ToolFilter(on_text)
            on_text = flt.feed
        if not think:
            sysmsg = (sysmsg + "\n\n" if sysmsg else "") + "Answer in at most two short sentences: you are being listened to."
        msgs = ([{"role": "system", "content": sysmsg}] if sysmsg else []) + messages
        if m["backend"] == "ollama":
            self._stream_ollama(m, msgs, on_text, think)
        else:
            self._stream_air(m, msgs[-8:], on_text)
        if flt and not self.stop.is_set():
            done = flt.finish(LANG[0])
            if done:
                flt.on_text(("\n\n" if flt.said else "") + done)

    def _stream_ollama(self, m, msgs, on_text, think=True):
        body = {"model": m["tag"], "messages": msgs, "stream": True, "keep_alive": "30m",
                "options": {"temperature": self.cfg["temperature"], "num_ctx": 4096,
                            "num_predict": int(self.cfg["max_tokens"])}}
        if not think:
            body["think"] = False
        thinking = False

        def post(b):
            return urllib.request.urlopen(urllib.request.Request(
                OLLAMA_API + "/api/chat", data=json.dumps(b).encode(), headers={"Content-Type": "application/json"}), timeout=600)

        try:
            r = post(body)
        except urllib.error.HTTPError as e:
            if e.code != 400 or think:
                raise
            body.pop("think")  # a model that knows nothing about "think": ask the usual way
            r = post(body)
        with r:
            for line in r:
                if self.stop.is_set():
                    return
                d = json.loads(line)
                if d.get("error"):
                    raise RuntimeError(d["error"])
                msg = d.get("message", {})
                if msg.get("thinking"):  # newer Ollama sends the reasoning apart
                    if not thinking:
                        on_text("<think>")
                        thinking = True
                    on_text(msg["thinking"])
                if msg.get("content"):
                    if thinking:
                        on_text("</think>")
                        thinking = False
                    on_text(msg["content"])
                if d.get("done"):
                    if thinking:
                        on_text("</think>")
                    return

    def _stream_air(self, m, msgs, on_text):
        w = self.air
        if not (w and w.alive() and self.air_ready):
            raise RuntimeError("MAX is not loaded")
        w.send(cmd="chat", messages=msgs, max_new_tokens=int(self.cfg["max_tokens_max"]),
               temperature=self.cfg["temperature"])
        stopped = False
        while True:
            if self.stop.is_set() and not stopped:
                w.send(cmd="stop")
                stopped = True
            e = w.get()
            if e is None:
                continue
            ev = e.get("event")
            if ev == "token":
                on_text(e["text"])
            elif ev == "done":
                return
            elif ev in ("error", "exit"):
                self.air_ready = False
                raise RuntimeError(e.get("msg") or "AirLLM stopped")

    def shutdown(self):
        self.stop_air()


# ---------------------------------------------------------------------------------------------- voice
def rms_of(chunk):
    a = array.array("h")
    a.frombytes(chunk[: len(chunk) // 2 * 2])
    if not a:
        return 0.0
    return math.sqrt(sum(x * x for x in a) / len(a))


class Voice:
    """Microphone capture with voice detection, speech to text, text to speech and playback."""

    def __init__(self, cfg, ui):
        self.cfg, self.ui = cfg, ui
        self.w = None
        self.player = None
        self.level = 0.0  # 0..1, what the orb shows (mic while listening, speech while speaking)
        self.cancel = threading.Event()
        self.mute_mic = threading.Event()  # voice mode: the microphone button is off
        self.hush = threading.Event()  # the speaker button is off: whatever is still being synthesized is dropped
        self.lang = LANG[0]  # language of the last thing the user said
        self.tmp = tempfile.mkdtemp(prefix="adai-voice-")
        self.stt_ready = False
        self.warned = set()

    def start(self, stt=True):
        """Starts the voice worker. Speech to text (a big model) is loaded only when asked for: reading answers aloud does not need it."""
        if not self.w or not self.w.alive():
            Env.ensure("voice", self.ui, self.cancel)
            self.w = JsonWorker("voice", on_log=lambda line: self.ui.progress(None, None, line))
            self.stt_ready = False
        if stt and not self.stt_ready:
            self.ui.progress(T("step_stt"), None)
            self.w.send(cmd="stt_load", size=self.cfg["stt_size"])
            self._wait("stt_ready", T("step_stt"))
            self.stt_ready = True
        self.ui.progress_done()

    def warn_once(self, key):
        """Tells the user about a problem with the sound setup, once per kind (a problem that goes away can be told again)."""
        if key not in self.warned:
            self.warned.add(key)
            self.ui.notice(T(key))

    @staticmethod
    def output_silent():
        """True if the default sound output is muted or at (almost) 0%."""
        try:
            out = subprocess.run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], capture_output=True, text=True, timeout=3).stdout
            return "[MUTED]" in out or float(out.split()[1]) < 0.03
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            return False

    def _wait(self, want, text):
        while True:
            e = self.w.get(self.cancel)
            if e is None:
                continue
            if e["event"] == want:
                return e
            if e["event"] == "status":
                self.ui.progress(T("step_voice") if e.get("key") == "downloading_voice" else text, None)
            if e["event"] in ("error", "exit"):
                raise RuntimeError(e.get("msg") or "voice worker stopped")

    def listen(self):
        """Records one utterance (waits for speech, stops after a pause). Returns a wav path or None."""
        p = subprocess.Popen(["parec", "--rate=16000", "--channels=1", "--format=s16le", "--latency-msec=40"],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.player = None
        chunk = 640  # 20 ms
        pre, voiced, silent_n, started, calib, floor_n = [], [], 0, False, [], 0
        t_start = time.time()
        try:
            while not self.cancel.is_set() and not self.mute_mic.is_set():
                b = p.stdout.read(chunk)
                if len(b) < chunk:
                    return None
                r = rms_of(b)
                self.level = min(1.0, r / 5000.0)
                if len(calib) < 20:  # first 0.4 s: measure the room
                    calib.append(r)
                    continue
                room = sum(calib) / len(calib)
                if room > 9000:  # clipping: speech cannot stand out of it
                    self.warn_once("mic_loud")
                thr = min(max(room * 2.8, 400.0), 12000.0)
                if not started:
                    pre = (pre + [b])[-15:]
                    floor_n = floor_n + 1 if r > thr else 0
                    if floor_n >= 3:
                        started, voiced, silent_n = True, list(pre), 0
                else:
                    voiced.append(b)
                    silent_n = silent_n + 1 if r < thr else 0
                    if silent_n > 28 or len(voiced) > 1500:  # 0.56 s of silence, or 30 s
                        break
                if not started and time.time() - t_start > 120:
                    return None
        finally:
            p.kill()
            self.level = 0.0
        if self.mute_mic.is_set() or not started or len(voiced) < 22:
            return None
        path = os.path.join(self.tmp, f"in-{int(time.time() * 1000)}.wav")
        with wave.open(path, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(b"".join(voiced))
        return path

    def transcribe(self, wav):
        lang = None if self.cfg["voice_lang"] == "auto" else self.cfg["voice_lang"]
        self.w.send(cmd="transcribe", wav=wav, lang=lang)
        e = self._wait("text", T("step_stt"))
        if e.get("lang") in VOICE_FOR:
            self.lang = e["lang"]
        try:
            os.remove(wav)
        except OSError:
            pass
        return e.get("text", "")

    def speak(self, text):
        """Synthesizes and plays text; blocks until it is over or cancelled."""
        text = text.strip()
        if not text or not self.cfg["tts"] or self.hush.is_set():
            return
        lang = self.cfg["voice_lang"] if self.cfg["voice_lang"] != "auto" else self.lang
        lang = lang if lang in VOICE_FOR else "en"
        c = self.cfg
        voice = VOICE_PRESETS.get(c["voice_preset"], VOICE_PRESETS["aurora"])["v"].get(lang, VOICE_FOR[lang])
        wav = os.path.join(self.tmp, f"out-{int(time.time() * 1000)}.wav")
        self.w.send(cmd="speak", text=text, wav=wav, voice=voice, length_scale=1.0 / max(0.3, c["voice_speed"]),
                    noise_scale=0.667 * c["voice_var"], noise_w=0.8 * c["voice_var"], volume=c["voice_volume"],
                    pitch=c["voice_pitch"], fx=c["voice_fx"])
        self._wait("spoken", T("step_voice"))
        self.ui.progress_done()
        if self.hush.is_set():
            try:
                os.remove(wav)
            except OSError:
                pass
            return
        self.play(wav)

    def play(self, wav):
        try:
            with wave.open(wav, "rb") as f:
                rate, n = f.getframerate(), f.getnframes()
                samples = array.array("h")
                samples.frombytes(f.readframes(n))
        except (OSError, wave.Error):
            return
        player = shutil.which("paplay") or shutil.which("pw-play") or shutil.which("aplay")
        if not player:
            return
        if self.output_silent():
            self.warn_once("sink_muted")
        else:
            self.warned.discard("sink_muted")
        self.player = subprocess.Popen([player, wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0, win = time.time(), int(rate * 0.04)
        try:
            while self.player and self.player.poll() is None:
                i = int((time.time() - t0) * rate)
                seg = samples[i:i + win]
                self.level = min(1.0, (math.sqrt(sum(x * x for x in seg) / len(seg)) if seg else 0) / 6000.0)
                time.sleep(0.03)
        finally:
            self.level = 0.0
            self.stop_playing()
            try:
                os.remove(wav)
            except OSError:
                pass

    def stop_playing(self):
        p, self.player = self.player, None
        if p and p.poll() is None:
            p.kill()

    def close(self):
        self.cancel.set()
        self.stop_playing()
        if self.w:
            self.w.close()
            self.w = None
        shutil.rmtree(self.tmp, ignore_errors=True)

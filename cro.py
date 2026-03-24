import tkinter as tk
from tkinter import scrolledtext
from threading import Thread, Lock
import speech_recognition as sr
import pyttsx3
import psutil
import webbrowser
import json
import requests
import os
import subprocess
import datetime
import pyautogui
import math
import random
import time
import re
import sys

# ─────────────────────────────────────────────
#  EDGE TTS  (async wrapper — graceful fallback)
# ─────────────────────────────────────────────
try:
    import edge_tts
    import asyncio
    import pygame
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

# ─────────────────────────────────────────────
#  OPTIONAL HEAVY IMPORTS
# ─────────────────────────────────────────────
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    import pywhatkit
    PYWHATKIT_AVAILABLE = True
except ImportError:
    PYWHATKIT_AVAILABLE = False

try:
    import pytesseract
    import numpy as np
    import cv2
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# ─────────────────────────────────────────────
#  GLOBALS
# ─────────────────────────────────────────────
running        = True
speech_lock    = Lock()
listening_started = False
tts_lock       = Lock()

# ─────────────────────────────────────────────
#  MEMORY / LEARN
# ─────────────────────────────────────────────
MEMORY_FILE = "memory.json"
LEARN_FILE  = "learn.json"

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

memory     = load_json(MEMORY_FILE)
learn_data = load_json(LEARN_FILE)

# ─────────────────────────────────────────────
#  FALLBACK TTS (pyttsx3)
# ─────────────────────────────────────────────
engine = pyttsx3.init('sapi5')
voices = engine.getProperty('voices')
if len(voices) > 1:
    engine.setProperty('voice', voices[0].id)
engine.setProperty('rate', 165)

# ─────────────────────────────────────────────
#  COLOURS / FONTS  (Jarvis palette)
# ─────────────────────────────────────────────
BG        = "#050d14"
PANEL     = "#071825"
ACCENT    = "#00d4ff"
ACCENT2   = "#00ff9d"
DIM       = "#1a4a5e"
TEXT      = "#cce8f0"
WARN      = "#ff6b35"
FONT_MONO = ("Courier New", 10)
FONT_HUD  = ("Courier New", 9, "bold")
FONT_TITLE= ("Courier New", 20, "bold")

# ─────────────────────────────────────────────
#  ROOT WINDOW
# ─────────────────────────────────────────────
root = tk.Tk()
root.title("CRO  —  MANI'S JARVIS")
root.geometry("900x720")
root.configure(bg=BG)
root.resizable(False, False)

# ══════════════════════════════════════════════
#  TOP HEADER BAR
# ══════════════════════════════════════════════
header = tk.Frame(root, bg=PANEL, height=56)
header.pack(fill="x")

tk.Label(header, text="◈ MS C-R-O  INTELLIGENCE SYSTEM",
         font=FONT_TITLE, fg=ACCENT, bg=PANEL).pack(side="left", padx=18, pady=10)

time_lbl = tk.Label(header, text="", font=FONT_HUD, fg=ACCENT2, bg=PANEL)
time_lbl.pack(side="right", padx=18)

def tick_clock():
    time_lbl.config(text=datetime.datetime.now().strftime("  %H:%M:%S   %d %b %Y  "))
    root.after(1000, tick_clock)

tick_clock()

# thin divider
tk.Frame(root, bg=ACCENT, height=1).pack(fill="x")

# ══════════════════════════════════════════════
#  MAIN BODY — left canvas + right panels
# ══════════════════════════════════════════════
body = tk.Frame(root, bg=BG)
body.pack(fill="both", expand=True, padx=0, pady=0)

# ── LEFT: ORB CANVAS ──────────────────────────
left = tk.Frame(body, bg=BG, width=320)
left.pack(side="left", fill="y")
left.pack_propagate(False)

orb_canvas = tk.Canvas(left, width=320, height=320, bg=BG, highlightthickness=0)
orb_canvas.pack(pady=(18,0))

# ── RIGHT: CHAT + HUD ─────────────────────────
right = tk.Frame(body, bg=BG)
right.pack(side="right", fill="both", expand=True, padx=(0,12))

# status bar under header
status_lbl = tk.Label(right, text="●  SYSTEM STANDBY",
                      font=("Courier New", 10, "bold"), fg=DIM, bg=BG, anchor="w")
status_lbl.pack(fill="x", pady=(10, 2))

# chat box
chat_frame = tk.Frame(right, bg=DIM, bd=0)
chat_frame.pack(fill="both", expand=True)

chat_box = scrolledtext.ScrolledText(
    chat_frame, height=22, bg="#030c14", fg=TEXT,
    font=FONT_MONO, insertbackground=ACCENT,
    relief="flat", bd=0, wrap="word",
    selectbackground=DIM, selectforeground=ACCENT
)
chat_box.pack(fill="both", expand=True, padx=1, pady=1)
chat_box.tag_config("cro",  foreground=ACCENT,  font=("Courier New", 10, "bold"))
chat_box.tag_config("user", foreground=ACCENT2, font=("Courier New", 10, "bold"))
chat_box.tag_config("sys",  foreground=WARN,    font=("Courier New", 9,  "italic"))

# input row
input_row = tk.Frame(right, bg=PANEL, height=40)
input_row.pack(fill="x", pady=(4, 0))

cmd_entry = tk.Entry(input_row, bg="#030c14", fg=ACCENT, font=FONT_MONO,
                     insertbackground=ACCENT, relief="flat", bd=6)
cmd_entry.pack(side="left", fill="x", expand=True, padx=(6,4), pady=6)

def send_text_cmd(event=None):
    txt = cmd_entry.get().strip()
    if txt:
        cmd_entry.delete(0, "end")
        Thread(target=run_command, args=(txt.lower(),), daemon=True).start()

cmd_entry.bind("<Return>", send_text_cmd)

send_btn = tk.Button(input_row, text="SEND ▶", font=FONT_HUD,
                     fg=BG, bg=ACCENT, activebackground=ACCENT2,
                     relief="flat", bd=0, padx=10, command=send_text_cmd)
send_btn.pack(side="right", padx=(0,6), pady=6)

# ── HUD ROW ───────────────────────────────────
hud = tk.Frame(root, bg=PANEL, height=44)
hud.pack(fill="x", side="bottom")
tk.Frame(root, bg=DIM, height=1).pack(fill="x", side="bottom")

cpu_lbl  = tk.Label(hud, text="CPU  0%",  font=FONT_HUD, fg=ACCENT2, bg=PANEL)
ram_lbl  = tk.Label(hud, text="RAM  0%",  font=FONT_HUD, fg=ACCENT2, bg=PANEL)
bat_lbl  = tk.Label(hud, text="BAT  --",  font=FONT_HUD, fg=ACCENT2, bg=PANEL)
mic_lbl  = tk.Label(hud, text="⬤ MIC OFF",font=FONT_HUD, fg=DIM,     bg=PANEL)

for w in (cpu_lbl, ram_lbl, bat_lbl):
    w.pack(side="left", padx=20, pady=10)
mic_lbl.pack(side="right", padx=20)

# ── BUTTON ROW under left canvas ─────────────
btn_row = tk.Frame(left, bg=BG)
btn_row.pack(pady=8)

def make_btn(parent, text, cmd, color=ACCENT):
    return tk.Button(parent, text=text, font=FONT_HUD,
                     fg=BG, bg=color, activebackground=ACCENT2,
                     relief="flat", bd=0, padx=10, pady=5, command=cmd)

start_btn = make_btn(btn_row, "▶  START",  lambda: Thread(target=start_jarvis, daemon=True).start())
stop_btn  = make_btn(btn_row, "■  STOP",   lambda: stop_assistant(), WARN)
start_btn.pack(side="left", padx=6)
stop_btn.pack(side="left",  padx=6)

# ══════════════════════════════════════════════
#  ORB ANIMATION  (multi-ring Jarvis style)
# ══════════════════════════════════════════════
orb_angle   = 0
orb_talking = False
orb_pulse   = 0

def draw_orb():
    global orb_angle, orb_pulse
    orb_canvas.delete("all")

    cx, cy = 160, 160

    # outer glow rings
    for i, (r, alpha) in enumerate([(110,0.08),(95,0.12),(80,0.18)]):
        shade = int(alpha * 255)
        col   = f"#{shade:02x}{min(shade*3,255):02x}{min(shade*5,255):02x}"
        orb_canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                outline=col, width=1, fill="")

    # rotating dashed ring
    for i in range(24):
        a    = math.radians(orb_angle + i * 15)
        r1, r2 = 90, 98
        x1 = cx + r1 * math.cos(a); y1 = cy + r1 * math.sin(a)
        x2 = cx + r2 * math.cos(a); y2 = cy + r2 * math.sin(a)
        orb_canvas.create_line(x1, y1, x2, y2, fill=DIM, width=1)

    # spokes
    for i in range(8):
        a  = math.radians(orb_angle * 1.5 + i * 45)
        r  = 65
        x1 = cx + 20 * math.cos(a); y1 = cy + 20 * math.sin(a)
        x2 = cx + r  * math.cos(a); y2 = cy + r  * math.sin(a)
        orb_canvas.create_line(x1, y1, x2, y2, fill=ACCENT, width=1)

    # talking wave dots
    if orb_talking:
        for i in range(16):
            a    = math.radians(orb_angle * 2 + i * 22.5)
            wave = 55 + 18 * math.sin(math.radians(orb_pulse + i * 30))
            x    = cx + wave * math.cos(a)
            y    = cy + wave * math.sin(a)
            s    = random.randint(2, 5)
            orb_canvas.create_oval(x-s, y-s, x+s, y+s, fill=ACCENT2, outline="")

    # core glow
    pulse_r = 32 + 6 * math.sin(math.radians(orb_pulse))
    orb_canvas.create_oval(cx-pulse_r-8, cy-pulse_r-8,
                            cx+pulse_r+8, cy+pulse_r+8,
                            fill="#001a2e", outline=DIM, width=1)
    orb_canvas.create_oval(cx-pulse_r, cy-pulse_r,
                            cx+pulse_r, cy+pulse_r,
                            fill="#002a40", outline=ACCENT, width=2)

    # inner cross
    for a_off in (0, 90):
        a  = math.radians(orb_angle + a_off)
        r  = pulse_r - 4
        x1 = cx + r * math.cos(a);  y1 = cy + r * math.sin(a)
        x2 = cx - r * math.cos(a);  y2 = cy - r * math.sin(a)
        orb_canvas.create_line(x1, y1, x2, y2, fill=ACCENT, width=1)

    # centre dot
    orb_canvas.create_oval(cx-5, cy-5, cx+5, cy+5, fill=ACCENT, outline="")

    orb_angle += 2
    orb_pulse += 6
    root.after(50, draw_orb)

draw_orb()

# ══════════════════════════════════════════════
#  HUD UPDATE
# ══════════════════════════════════════════════
def update_hud():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    try:
        bat = psutil.sensors_battery()
        bat_txt = f"BAT  {int(bat.percent)}%"
    except:
        bat_txt = "BAT  N/A"
    cpu_lbl.config(text=f"CPU  {cpu}%")
    ram_lbl.config(text=f"RAM  {ram}%")
    bat_lbl.config(text=bat_txt)
    root.after(4000, update_hud)

update_hud()

# ══════════════════════════════════════════════
#  CHAT HELPER
# ══════════════════════════════════════════════
def chat_append(who, text):
    tag = who.lower()
    prefix = {"cro": "◈ CRO  › ", "you": "▸ YOU  › ", "sys": "⚙ SYS  › "}.get(tag, "")
    chat_box.insert("end", f"\n{prefix}", tag)
    chat_box.insert("end", text, "")
    chat_box.see("end")

# ══════════════════════════════════════════════
#  SPEAK
# ══════════════════════════════════════════════
def speak(text):
    chat_append("cro", text)
    status_lbl.config(text="●  SPEAKING...", fg=ACCENT)
    global orb_talking
    orb_talking = True

    def _do():
        global orb_talking
        with tts_lock:
            if EDGE_TTS_AVAILABLE:
                _speak_edge(text)
            else:
                engine.say(text)
                engine.runAndWait()
        orb_talking = False
        status_lbl.config(text="●  WAITING FOR COMMAND...", fg=DIM)

    Thread(target=_do, daemon=True).start()

def _speak_edge(text):
    tmp_path = None
    try:
        import asyncio, tempfile

        async def _run(path):
            communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
            await communicate.save(path)

        # MP3 — edge-tts natively outputs MP3
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
        os.close(tmp_fd)

        asyncio.run(_run(tmp_path))

        # fresh pygame init every time
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()

        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.05)

        # fully release before delete
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        time.sleep(0.2)

    except Exception as e:
        print("Edge TTS error:", e)
        engine.say(text)
        engine.runAndWait()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            for _ in range(8):
                try:
                    os.unlink(tmp_path)
                    break
                except PermissionError:
                    time.sleep(0.3)

# ══════════════════════════════════════════════
#  LISTEN
# ══════════════════════════════════════════════
def listen():
    r = sr.Recognizer()
    r.energy_threshold = 300
    with speech_lock:
        with sr.Microphone() as source:
            try:
                mic_lbl.config(text="⬤ LISTENING", fg=ACCENT2)
                status_lbl.config(text="●  LISTENING...", fg=ACCENT2)
                r.adjust_for_ambient_noise(source, duration=0.4)
                audio = r.listen(source, timeout=6, phrase_time_limit=6)
                text  = r.recognize_google(audio).lower()
                chat_append("you", text)
                return text
            except:
                return ""
            finally:
                mic_lbl.config(text="⬤ MIC OFF", fg=DIM)
                status_lbl.config(text="●  WAITING FOR COMMAND...", fg=DIM)

# ══════════════════════════════════════════════
#  WAKE WORD
# ══════════════════════════════════════════════
def wait_for_wake():
    r = sr.Recognizer()
    r.energy_threshold = 250
    r.dynamic_energy_threshold = True
    chat_append("sys", "Waiting for wake word  'Hey Cro'...")
    while running:
        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                try:
                    audio = r.listen(source, timeout=5, phrase_time_limit=4)
                    txt   = r.recognize_google(audio).lower()
                    print("Wake heard:", txt)
                    if any(w in txt for w in ("hey cro", "ok cro", "hello cro", "hey crow", "a cro")):
                        return True
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    chat_append("sys", f"Speech service error: {e}")
                    time.sleep(2)
        except Exception as e:
            print("Wake loop error:", e)
            time.sleep(1)
    return False

# ══════════════════════════════════════════════
#  AI
# ══════════════════════════════════════════════
def ask_ai(q):
    if OLLAMA_AVAILABLE:
        try:
            res = ollama.chat(model="phi3",
                              messages=[{"role": "user", "content": q}])
            return res["message"]["content"]
        except:
            pass
    return "Sorry boss, AI model not available right now."

def generate_code(task):
    prompt = f"Return ONLY Python code, no explanation, no ```, no comments.\nTask: {task}"
    raw = ask_ai(prompt)
    raw = re.sub(r"```.*?```", "", raw, flags=re.DOTALL)
    raw = raw.replace("```python","").replace("```","")
    return raw.strip() or 'print("Hello from CRO")'

def create_python_file(task):
    code     = generate_code(task)
    filename = "ai_generated.py"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)
    speak("Code created boss")
    return filename

def run_python_file(file):
    speak("Running the code")
    subprocess.Popen(["python", file])

# ══════════════════════════════════════════════
#  WEATHER
# ══════════════════════════════════════════════
def get_weather(city):
    api_key = "fa1daef5ea8c0588513191a2f797a5b1"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        data = requests.get(url, timeout=5).json()
        if data.get("cod") != 200:
            return f"Couldn't find weather for {city}"
        return f"{city}: {data['main']['temp']}°C, {data['weather'][0]['description']}"
    except:
        return "Weather service not working boss"

# ══════════════════════════════════════════════
#  COMMAND ENGINE
# ══════════════════════════════════════════════
def run_command(cmd):
    global running, memory
    chat_append("sys", f"CMD → {cmd}")

    # learned commands
    if cmd in learn_data:
        speak(f"Executing learned command: {cmd}")
        os.system(learn_data[cmd])
        return

    # ── SEARCH ──────────────────────────────
    if "search" in cmd and "youtube" not in cmd:
        topic = cmd.replace("search", "").strip()
        webbrowser.open(f"https://www.google.com/search?q={topic}")
        speak(f"Searching {topic}")

    # ── PLAY YOUTUBE ────────────────────────
    elif "play" in cmd:
        song = cmd.replace("play", "").strip()
        speak(f"Playing {song}")
        if PYWHATKIT_AVAILABLE:
            pywhatkit.playonyt(song)
        else:
            webbrowser.open(f"https://www.youtube.com/search?q={song}")

    # ── WEBSITES ────────────────────────────
    elif "open youtube"   in cmd: webbrowser.open("https://youtube.com");  speak("Opening YouTube")
    elif "open google"    in cmd: webbrowser.open("https://google.com");   speak("Opening Google")
    elif "open gmail"     in cmd: webbrowser.open("https://mail.google.com"); speak("Opening Gmail")
    elif "open whatsapp"  in cmd: webbrowser.open("https://web.whatsapp.com"); speak("Opening WhatsApp")
    elif "open github"    in cmd: webbrowser.open("https://github.com");   speak("Opening GitHub")
    elif "open website"   in cmd:
        site = cmd.replace("open website", "").strip()
        webbrowser.open(f"https://{site}.com")
        speak(f"Opening {site}")

    # ── APPS ────────────────────────────────
    elif "open notepad"    in cmd: subprocess.Popen("notepad.exe");       speak("Opening Notepad")
    elif "open calculator" in cmd: subprocess.Popen("calc.exe");          speak("Opening Calculator")
    elif "open chrome"     in cmd: subprocess.Popen("start chrome", shell=True); speak("Opening Chrome")

    # ── CLOSE APPS ──────────────────────────
    elif "close notepad"    in cmd: os.system("taskkill /f /im notepad.exe")
    elif "close chrome"     in cmd: os.system("taskkill /f /im chrome.exe")
    elif "close calculator" in cmd: os.system("taskkill /f /im calc.exe")

    # ── VOLUME ──────────────────────────────
    elif "volume up"   in cmd: pyautogui.press("volumeup");   speak("Volume up")
    elif "volume down" in cmd: pyautogui.press("volumedown"); speak("Volume down")
    elif "mute"        in cmd: pyautogui.press("volumemute"); speak("Muted")

    # ── WINDOW CONTROL ──────────────────────
    elif "minimize" in cmd:      pyautogui.hotkey("win", "down")
    elif "maximize" in cmd:      pyautogui.hotkey("win", "up")
    elif "switch window" in cmd: pyautogui.hotkey("alt", "tab")
    elif "scroll down"   in cmd: pyautogui.scroll(-500); speak("Scrolling down")
    elif "scroll up"     in cmd: pyautogui.scroll(500);  speak("Scrolling up")

    # ── SCREENSHOT ──────────────────────────
    elif "screenshot" in cmd:
        f = f"screenshot_{datetime.datetime.now().strftime('%H%M%S')}.png"
        pyautogui.screenshot(f)
        speak(f"Screenshot saved as {f}")

    # ── TIME / DATE ─────────────────────────
    elif "time" in cmd: speak(datetime.datetime.now().strftime("%I:%M %p"))
    elif "date" in cmd: speak(datetime.datetime.now().strftime("%d %B %Y"))

    # ── WEATHER ─────────────────────────────
    elif "weather in" in cmd:
        city = cmd.split("weather in")[-1].strip()
        speak(get_weather(city))
    elif "weather" in cmd:
        speak(get_weather("Chennai"))

    # ── SYSTEM STATS ────────────────────────
    elif "cpu" in cmd:     speak(f"CPU usage is {psutil.cpu_percent()} percent")
    elif "ram" in cmd:     speak(f"RAM usage is {psutil.virtual_memory().percent} percent")
    elif "battery" in cmd:
        b = psutil.sensors_battery()
        speak(f"Battery is {int(b.percent)} percent" if b else "Battery info not available")

    # ── SHUTDOWN / RESTART ──────────────────
    elif "shutdown" in cmd: os.system("shutdown /s /t 5");  speak("Shutting down in 5 seconds")
    elif "restart"  in cmd: os.system("shutdown /r /t 5");  speak("Restarting in 5 seconds")

    # ── MEMORY ──────────────────────────────
    elif cmd.startswith("remember"):
        try:
            data = cmd.replace("remember", "").strip()
            k, v = data.split(" is ")
            memory[k.strip()] = v.strip()
            save_json(MEMORY_FILE, memory)
            speak(f"Got it boss, I'll remember that")
        except:
            speak("Say: remember something is something")
    elif "what is my name" in cmd:
        speak(f"Your name is {memory.get('name', 'unknown boss')}")
    elif "my name is" in cmd:
        name = cmd.replace("my name is", "").strip()
        memory["name"] = name
        save_json(MEMORY_FILE, memory)
        speak(f"Nice to meet you {name}")

    # ── CODE GENERATION ─────────────────────
    elif "create python code" in cmd or "write code" in cmd:
        task = re.sub(r"(create python code|write code)", "", cmd).strip()
        f    = create_python_file(task)
        run_python_file(f)

    # ── AI MODE ─────────────────────────────
    elif "start ai mode" in cmd:
        speak("AI mode started. Ask me anything. Say stop AI to exit.")
        while True:
            q = listen()
            if not q: continue
            if "stop ai" in q:
                speak("Exiting AI mode");  break
            speak(ask_ai(q)[:400])

    # ── STOP ────────────────────────────────
    elif "stop" in cmd and "assistant" in cmd:
        speak("Shutting down. Goodbye boss.")
        running = False

    # ── AI FALLBACK ─────────────────────────
    else:
        if cmd in memory:
            speak(memory[cmd])
        else:
            answer = ask_ai(cmd)
            speak(answer[:400])

# ══════════════════════════════════════════════
#  JARVIS LOOP
# ══════════════════════════════════════════════
def jarvis_loop():
    global running
    speak("CRO online. Say Hey Cro to activate.")
    while running:
        try:
            woke = wait_for_wake()
            if woke:
                speak("Yes boss, I'm listening.")
                while running:
                    cmd = listen()
                    if not cmd: continue
                    if "stop listening" in cmd or "sleep" in cmd:
                        speak("Going to sleep. Say Hey Cro to wake me.")
                        break
                    Thread(target=run_command, args=(cmd,), daemon=True).start()
        except Exception as e:
            chat_append("sys", f"Loop error: {e}")
            time.sleep(1)

def start_jarvis():
    global listening_started
    if not listening_started:
        listening_started = True
        Thread(target=jarvis_loop, daemon=True).start()
    else:
        speak("Already running boss")

def stop_assistant():
    global running
    running = False
    speak("Stopping assistant")

# ══════════════════════════════════════════════
#  STARTUP CHAT BANNER
# ══════════════════════════════════════════════
chat_append("sys", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
chat_append("sys", "  C.R.O  INTELLIGENCE SYSTEM  v2.0")
chat_append("sys", "  Built by MANI  |  Jarvis Edition")
chat_append("sys", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
chat_append("sys", "  Press ▶ START  or  type a command below")

root.mainloop()
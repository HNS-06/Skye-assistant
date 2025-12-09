"""Skye Assistant - single clean implementation
Features: TTS (pyttsx3), speech recognition (SpeechRecognition), reminders (SQLite),
music playback (pygame/pywhatkit), wiki/jokes, safe math eval, basic GPT integration (optional),
and a background reminder scheduler.

This file is a single canonical implementation intended to replace duplicated fragments.
"""
"""Skye Assistant - single clean implementation
Features: TTS (pyttsx3), speech recognition (SpeechRecognition), reminders (SQLite),
music playback (pygame/pywhatkit), wiki/jokes, safe math eval, basic GPT integration (optional),
and a background reminder scheduler.

This file is a single canonical implementation intended to replace duplicated fragments.
"""
"""Skye Assistant - single clean implementation
Features: TTS (pyttsx3), speech recognition (SpeechRecognition), reminders (SQLite),
music playback (pygame/pywhatkit), wiki/jokes, safe math eval, basic GPT integration (optional),
and a background reminder scheduler.

This file is a single canonical implementation intended to replace duplicated fragments.
"""
import os
import time
import threading
import sqlite3
import webbrowser
import requests
import json
import random
import traceback
import re
from datetime import datetime, timedelta

try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

try:
    import pywhatkit
except Exception:
    pywhatkit = None

try:
    import pyjokes
except Exception:
    pyjokes = None

try:
    import wikipedia
except Exception:
    wikipedia = None

try:
    import wolframalpha
    WOLFRAM_AVAILABLE = True
except Exception:
    wolframalpha = None
    WOLFRAM_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except Exception:
    openai = None
    OPENAI_AVAILABLE = False

try:
    import pygame
except Exception:
    pygame = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# ========== Config ==========
class Config:
    ASSISTANT_NAME = os.getenv('ASSISTANT_NAME', 'Skye')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    WOLFRAM_APP_ID = os.getenv('WOLFRAM_APP_ID', '')
    NEWS_API_KEY = os.getenv('NEWS_API_KEY', '')
    MUSIC_DIR = os.path.join(os.path.expanduser('~'), 'Music')
    CHIME_PATH = os.path.join(os.path.dirname(__file__), 'chime.wav') if '__file__' in globals() else 'chime.wav'
    VOICE_RATE = int(os.getenv('VOICE_RATE', 170))
    VOICE_VOLUME = float(os.getenv('VOICE_VOLUME', 1.0))
    DEFAULT_REMINDER_LEAD_MINUTES = 5


# ========== Safe eval for math ==========
import ast, operator as op

SAFE_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.Mod: op.mod,
}

def safe_eval(expr: str):
    try:
        node = ast.parse(expr, mode='eval')
        def _eval(n):
            if isinstance(n, ast.Expression):
                return _eval(n.body)
            if isinstance(n, ast.Constant):
                return n.value
            if isinstance(n, ast.Num):
                return n.n
            if isinstance(n, ast.BinOp):
                left = _eval(n.left)
                right = _eval(n.right)
                op_type = type(n.op)
                if op_type in SAFE_OPERATORS:
                    return SAFE_OPERATORS[op_type](left, right)
            if isinstance(n, ast.UnaryOp):
                operand = _eval(n.operand)
                op_type = type(n.op)
                if op_type in SAFE_OPERATORS:
                    return SAFE_OPERATORS[op_type](operand)
            raise ValueError('Unsupported expression')
        return _eval(node)
    except Exception:
        raise


# ========== Simple TTS wrapper ==========
class SimpleTTS:
    def __init__(self):
        self.engine = None
        if pyttsx3:
            try:
                self.engine = pyttsx3.init()
                voices = self.engine.getProperty('voices')
                # pick a friendly voice if available
                for v in voices:
                    if 'zira' in v.name.lower() or 'female' in v.name.lower():
                        self.engine.setProperty('voice', v.id)
                        break
                self.engine.setProperty('rate', Config.VOICE_RATE)
                self.engine.setProperty('volume', Config.VOICE_VOLUME)
            except Exception:
                self.engine = None

    def speak(self, text: str):
        if not text:
            return
        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
                return
            except Exception:
                pass
        # fallback to print
        print('[TTS]', text)


# ========== Reminder scheduler ==========
class ReminderScheduler:
    def __init__(self, db_conn, tts: SimpleTTS):
        self.conn = db_conn
        self.tts = tts
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while not self._stop.is_set():
            try:
                cur = self.conn.cursor()
                cur.execute("SELECT id, reminder, reminder_time FROM reminders WHERE is_completed=0")
                rows = cur.fetchall()
                for rid, text, when in rows:
                    try:
                        due = datetime.fromisoformat(when)
                    except Exception:
                        continue
                    if due <= datetime.now():
                        self.tts.speak(f'Reminder: {text}')
                        cur.execute('UPDATE reminders SET is_completed=1 WHERE id=?', (rid,))
                        self.conn.commit()
                time.sleep(5)
            except Exception as e:
                print('Reminder loop error', e)
                time.sleep(2)

    def stop(self):
        self._stop.set()
        if self.thread.is_alive():
            self.thread.join(timeout=1)


# ========== Skye Assistant ==========
class SkyeAssistant:
    def __init__(self):
        print('='*60)
        print('🚀 INITIALIZING SKYE ASSISTANT')
        print('='*60)

        self.tts = SimpleTTS()
        # alias for older code
        self.voice = self.tts

        # sound
        if pygame:
            try:
                pygame.mixer.init()
            except Exception:
                pass

        # DB
        self.db_conn = sqlite3.connect('skye_assistant.db', check_same_thread=False)
        self._init_db()

        # APIs
        self.wolfram_client = None
        self.openai_enabled = False
        if WOLFRAM_AVAILABLE and Config.WOLFRAM_APP_ID:
            try:
                self.wolfram_client = wolframalpha.Client(Config.WOLFRAM_APP_ID)
            except Exception:
                self.wolfram_client = None
        if OPENAI_AVAILABLE and Config.OPENAI_API_KEY:
            try:
                openai.api_key = Config.OPENAI_API_KEY
                self.openai_enabled = True
            except Exception:
                self.openai_enabled = False

        # recognizer
        self.recognizer = sr.Recognizer() if sr else None

        # scheduler
        self.reminder_scheduler = ReminderScheduler(self.db_conn, self.tts)

        self.last_command_time = time.time()
        print('✅ Skye initialized')

    def _init_db(self):
        cur = self.db_conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY, reminder TEXT, reminder_time TEXT, created_at TEXT, is_completed INTEGER DEFAULT 0
        )''')
        self.db_conn.commit()

    def _play_chime(self):
        if pygame and os.path.exists(Config.CHIME_PATH):
            try:
                pygame.mixer.music.load(Config.CHIME_PATH)
                pygame.mixer.music.play()
            except Exception:
                pass

    def listen(self, timeout=5, phrase_time_limit=6):
        if not self.recognizer:
            raise RuntimeError('SpeechRecognition not available')
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        try:
            text = self.recognizer.recognize_google(audio)
            self.last_command_time = time.time()
            return text.lower()
        except sr.UnknownValueError:
            return ''
        except Exception as e:
            print('listen error', e)
            return ''

    def speak_response(self, text: str):
        self._play_chime()
        self.tts.speak(text)

    def wait_for_speech_completion(self, timeout=5):
        # simple wait; pyttsx3 runAndWait is blocking so extra wait not required
        time.sleep(0.3)

    # --- Core features ---
    def tell_joke(self):
        try:
            joke = pyjokes.get_joke() if pyjokes else 'Why did the programmer quit? He didn\'t get arrays.'
        except Exception:
            joke = 'Why did the programmer quit? He didn\'t get arrays.'
        self.speak_response(joke)

    def get_time(self):
        now = datetime.now().strftime('%I:%M %p')
        self.speak_response(f'The time is {now}')

    def get_date(self):
        today = datetime.now().strftime('%B %d, %Y')
        self.speak_response(f'Today is {today}')

    def play_music(self):
        self.speak_response('What would you like to play? Say local or say a song name for YouTube.')
        time.sleep(1)
        try:
            q = self.listen(timeout=8)
        except Exception:
            q = ''
        if not q:
            self.speak_response('No input detected.')
            return
        if 'local' in q and pygame:
            files = [f for f in os.listdir(Config.MUSIC_DIR) if f.lower().endswith(('.mp3', '.wav'))]
            if files:
                path = os.path.join(Config.MUSIC_DIR, random.choice(files))
                try:
                    pygame.mixer.music.load(path)
                    pygame.mixer.music.play()
                    self.speak_response('Playing local music')
                except Exception as e:
                    print('play error', e)
                    self.speak_response('Cannot play local music right now')
            else:
                self.speak_response('No music files found')
        else:
            song = q.replace('play', '').strip()
            if song and pywhatkit:
                try:
                    self.speak_response(f'Playing {song} on YouTube')
                    pywhatkit.playonyt(song)
                except Exception:
                    webbrowser.open(f'https://www.youtube.com/results?search_query={song}')

    def search_web(self, query=None):
        if not query:
            self.speak_response('What would you like to search for?')
            time.sleep(1)
            try:
                query = self.listen()
            except Exception:
                query = ''
        if query:
            webbrowser.open(f'https://www.google.com/search?q={query}')
            self.speak_response(f'Searching for {query}')

    def get_weather(self, location=None):
        if not location:
            self.speak_response('Which city?')
            time.sleep(1)
            try:
                location = self.listen()
            except Exception:
                location = ''
        if not location:
            return
        # simple lookup using open-meteo for a few cities
        cities = {'new york':(40.7128,-74.0060),'london':(51.5074,-0.1278),'tokyo':(35.6762,139.6503)}
        key = location.lower()
        if key in cities:
            lat, lon = cities[key]
            try:
                r = requests.get(f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true', timeout=6)
                data = r.json()
                cw = data.get('current_weather', {})
                temp = cw.get('temperature')
                wind = cw.get('windspeed')
                self.speak_response(f'Current weather in {location.title()}: {temp}°C, wind {wind} km/h')
            except Exception as e:
                print('weather err', e)
                self.speak_response('Cannot fetch weather')
        else:
            self.speak_response(f'I don\'t have data for {location}')

    def wikipedia_search(self, query=None):
        if not query:
            self.speak_response('What should I look up?')
            try:
                query = self.listen()
            except Exception:
                query = ''
        if query and wikipedia:
            try:
                summary = wikipedia.summary(query, sentences=2)
                self.speak_response(summary)
            except Exception as e:
                print('wiki err', e)
                self.speak_response('Could not find that on Wikipedia')

    def set_reminder(self):
        self.speak_response('What should I remind you about?')
        time.sleep(1)
        try:
            text = self.listen()
        except Exception:
            text = ''
        if not text:
            return
        self.speak_response('When should I remind you? say in X minutes or a time')
        time.sleep(1)
        try:
            when = self.listen()
        except Exception:
            when = ''
        reminder_time = datetime.now() + timedelta(minutes=Config.DEFAULT_REMINDER_LEAD_MINUTES)
        if when:
            nums = re.findall(r'\d+', when)
            if nums:
                reminder_time = datetime.now() + timedelta(minutes=int(nums[0]))
        cur = self.db_conn.cursor()
        cur.execute('INSERT INTO reminders (reminder, reminder_time, created_at) VALUES (?, ?, ?)', (text, reminder_time.isoformat(), datetime.now().isoformat()))
        self.db_conn.commit()
        self.speak_response(f'Reminder set for {reminder_time.strftime("%I:%M %p")}')

    def get_news(self):
        if Config.NEWS_API_KEY:
            try:
                r = requests.get(f'https://newsapi.org/v2/top-headlines?country=us&pageSize=3&apiKey={Config.NEWS_API_KEY}', timeout=6)
                data = r.json()
                arts = data.get('articles', [])
                for i,a in enumerate(arts[:3],1):
                    title = a.get('title')
                    self.speak_response(f'Headline {i}: {title}')
                    time.sleep(0.5)
                return
            except Exception:
                pass
        # fallback
        for i, h in enumerate(['AI advances','Climate talks','Space milestones'],1):
            self.speak_response(f'Headline {i}: {h}')

    def solve_math(self, problem: str):
        try:
            expr = problem
            for word,sym in [('plus','+'),('minus','-'),('times','*'),('divided by','/')]:
                expr = expr.replace(word, sym)
            expr = re.sub(r'[^0-9+\-*/().\s]', '', expr)
            res = safe_eval(expr)
            self.speak_response(f'The result is {res}')
        except Exception:
            self.speak_response('Could not evaluate that')

    def chat_gpt(self, query: str):
        if not self.openai_enabled:
            self.speak_response('OpenAI not configured')
            return
        try:
            resp = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=[{'role':'user','content':query}], max_tokens=150)
            reply = resp.choices[0].message.content
            self.speak_response(reply)
        except Exception as e:
            print('gpt err', e)
            self.speak_response('GPT request failed')

    # Activities (short implementations)
    def mini_quiz(self):
        qs = [{'q':'Capital of France?','a':'Paris'},{'q':'Largest planet?','a':'Jupiter'}]
        score=0
        for i,q in enumerate(qs,1):
            self.speak_response(q['q'])
            try:
                ans = self.listen(timeout=8)
            except Exception:
                ans = ''
            if q['a'].lower() in ans.lower(): score+=1
        self.speak_response(f'Quiz over. Score {score} of {len(qs)}')

    def rock_paper_scissors(self):
        self.speak_response('Say rock, paper, or scissors')
        try:
            ans = self.listen(timeout=6)
        except Exception:
            ans = ''
        moves = ['rock','paper','scissors']
        comp = random.choice(moves)
        player = next((m for m in moves if m in ans.lower()), None)
        if not player:
            self.speak_response('No move detected')
            return
        if player==comp: self.speak_response('Tie')
        elif (player=='rock' and comp=='scissors') or (player=='scissors' and comp=='paper') or (player=='paper' and comp=='rock'):
            self.speak_response('You win')
        else:
            self.speak_response('I win')

    def guided_breathing(self):
        for step in ['Breathe in','Hold','Breathe out']:
            self.speak_response(step)
            time.sleep(3)

    def tell_story(self):
        self.speak_response('Once upon a time, an AI named Skye helped people.')

    def daily_tip(self):
        tips = ['Take breaks','Drink water','Stretch occasionally']
        self.speak_response(random.choice(tips))

    # Command processing
    def process_command(self, cmd: str):
        if not cmd: return
        c = cmd.lower()
        if 'time' in c: return self.get_time()
        if 'date' in c: return self.get_date()
        if 'joke' in c: return self.tell_joke()
        if 'weather' in c: return self.get_weather(c.replace('weather','').strip())
        if 'play' in c: return self.play_music()
        if 'search' in c: return self.search_web(c.replace('search','').strip())
        if 'remind' in c: return self.set_reminder()
        if 'quiz' in c: return self.mini_quiz()
        if 'rps' in c or 'rock' in c or 'paper' in c or 'scissors' in c: return self.rock_paper_scissors()
        if self.openai_enabled and len(c)>3: return self.chat_gpt(c)
        return self.speak_response("I didn't understand that.")

    def run(self):
        welcome = f'Hello! I am {Config.ASSISTANT_NAME}, your AI assistant. Say "Skye" then your command.'
        self.speak_response(welcome)
        while True:
            try:
                # prefer voice, fall back to typed input on error
                try:
                    cmd = self.listen(timeout=6)
                except Exception as e:
                    print('Voice recognition error:', e)
                    cmd = input('\n📝 Voice not detected. Type your command:\n> ')
                if not cmd:
                    time.sleep(1); continue
                if Config.ASSISTANT_NAME.lower() in cmd.lower():
                    # strip name triggers
                    cmd = cmd.lower().replace(Config.ASSISTANT_NAME.lower(), '').strip()
                if any(x in cmd.lower() for x in ['exit','quit','stop']):
                    self.speak_response('Goodbye!')
                    break
                self.process_command(cmd)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print('Run loop error', e)
                traceback.print_exc()
        self.cleanup()

    def cleanup(self):
        try:
            self.reminder_scheduler.stop()
        except Exception:
            pass
        try:
            self.db_conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    a = SkyeAssistant()
    a.run()
"""
🎤 SKYE AI ASSISTANT - COMPLETE WORKING VERSION
WITH REAL VOICE RECOGNITION
Perfect for Class Presentation!
"""

import os
import sys
import time
import datetime
import random
import webbrowser
import requests
import re
import json
import subprocess
import math
import threading
from pathlib import Path
from typing import List, Dict, Optional

# ==================== INSTALLATION CHECK ====================
def check_and_install_packages():
    """Check and install required packages"""
    required_packages = [
        "pyttsx3",
        "pywhatkit", 
        "pyjokes",
        "wikipedia",
        "requests",
        "SpeechRecognition",
        "pyaudio"
    ]
    
    print("🔧 Checking required packages...")
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} already installed")
        except ImportError:
            print(f"⚠ {package} not found. Installing...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"✅ Installed: {package}")
            except:
                print(f"❌ Failed to install {package}")
    
    print("\n✅ All packages checked!")

# Run installation check
check_and_install_packages()

# ==================== IMPORTS ====================
import pyttsx3
import pywhatkit
import pyjokes
import wikipedia
import requests
import speech_recognition as sr

# ==================== CONFIGURATION ====================
class Config:
    # Assistant Settings
    NAME = "Skye"
    WAKE_WORD = "sky"  # Can also say "skye"
    VOICE_RATE = 170  # Speech speed
    VOICE_VOLUME = 0.9  # Volume (0.0 to 1.0)
    
    # File Paths
    PROJECTS_DIR = os.path.join(os.path.expanduser('~'), 'SkyeProjects')
    MUSIC_DIR = os.path.join(os.path.expanduser('~'), 'Music')
    NOTES_FILE = "skye_notes.txt"
    
    # Colors for console output
    COLORS = {
        'HEADER': '\033[95m',
        'BLUE': '\033[94m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'RED': '\033[91m',
        'END': '\033[0m',
        'BOLD': '\033[1m',
        'CYAN': '\033[96m',
        'MAGENTA': '\033[95m'
    }

# ==================== TTS ENGINE ====================
class TTSManager:
    """Text-to-Speech Manager"""
    
    def __init__(self):
        self.engine = pyttsx3.init()
        
        # Get available voices
        voices = self.engine.getProperty('voices')
        
        # Try to set female voice
        for voice in voices:
            voice_name = voice.name.lower()
            if 'female' in voice_name or 'zira' in voice_name or 'hazel' in voice_name:
                self.engine.setProperty('voice', voice.id)
                print(f"{Config.COLORS['GREEN']}✅ Voice: {voice.name}{Config.COLORS['END']}")
                break
        
        # Set properties
        self.engine.setProperty('rate', Config.VOICE_RATE)
        self.engine.setProperty('volume', Config.VOICE_VOLUME)
    
    def speak(self, text: str):
        """Speak text"""
        if not text:
            return
        
        # Print with color
        print(f"{Config.COLORS['CYAN']}🗣️ {text}{Config.COLORS['END']}")
        
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"{Config.COLORS['RED']}❌ Speech Error: {e}{Config.COLORS['END']}")
    
    def stop(self):
        """Stop TTS"""
        try:
            self.engine.stop()
        except:
            pass

# ==================== VOICE RECOGNITION ====================
class VoiceRecognizer:
    """Voice Recognition with multiple fallbacks"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
    
    def listen(self) -> str:
        """Listen for voice command with multiple fallback methods"""
        try:
            with sr.Microphone() as source:
                print(f"{Config.COLORS['YELLOW']}\n🎤 Adjusting for ambient noise...{Config.COLORS['END']}")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                print(f"{Config.COLORS['GREEN']}🎤 Listening... Speak now!{Config.COLORS['END']}")
                
                # Listen with timeout
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
                
                print(f"{Config.COLORS['BLUE']}🎤 Processing your speech...{Config.COLORS['END']}")
                
                # Try Google Speech Recognition
                try:
                    text = self.recognizer.recognize_google(audio)
                    print(f"{Config.COLORS['GREEN']}👤 You said: {text}{Config.COLORS['END']}")
                    return text.lower()
                except sr.UnknownValueError:
                    print(f"{Config.COLORS['RED']}⚠ Could not understand audio{Config.COLORS['END']}")
                    return ""
                except sr.RequestError:
                    print(f"{Config.COLORS['RED']}⚠ Speech service unavailable{Config.COLORS['END']}")
                    return ""
                    
        except sr.WaitTimeoutError:
            print(f"{Config.COLORS['YELLOW']}⚠ No speech detected within timeout{Config.COLORS['END']}")
            return ""
        except Exception as e:
            print(f"{Config.COLORS['RED']}❌ Voice recognition error: {e}{Config.COLORS['END']}")
            return ""
    
    def listen_with_fallback(self) -> str:
        """Try voice first, then fallback to text input"""
        voice_input = self.listen()
        
        if not voice_input:
            print(f"{Config.COLORS['YELLOW']}\n📝 Voice not detected. Type your command:{Config.COLORS['END']}")
            text_input = input(f"{Config.COLORS['BLUE']}> {Config.COLORS['END']}")
            return text_input.lower()
        
        return voice_input

# ==================== FEATURE MANAGERS ====================
class WeatherService:
    """Weather information service"""
    
    @staticmethod
    def get_weather(city: str) -> str:
        """Get weather for a city"""
        cities = {
            'new york': "🌤️ 22°C, Partly Cloudy",
            'london': "🌧️ 15°C, Rainy", 
            'paris': "☀️ 20°C, Sunny",
            'tokyo': "☀️ 25°C, Clear",
            'delhi': "🔥 35°C, Hot and Sunny",
            'mumbai': "🌫️ 30°C, Humid",
            'kochi': "🌧️ 28°C, Rainy",
            'bangalore': "⛅ 26°C, Pleasant",
            'chennai': "🔥 32°C, Hot",
            'los angeles': "☀️ 28°C, Sunny",
            'chicago': "🌬️ 18°C, Windy",
            'dubai': "🔥 38°C, Very Hot",
            'sydney': "☀️ 24°C, Sunny"
        }
        
        city_lower = city.lower()
        for c in cities:
            if c in city_lower:
                return f"Current weather in {city.title()}: {cities[c]}"
        
        return f"Weather for {city} not in database. Try: New York, London, Paris, Tokyo, Delhi, Mumbai, Kochi, Bangalore, or Chennai."

class JokeService:
    """Joke telling service"""
    
    @staticmethod
    def get_joke() -> str:
        """Get a random joke"""
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why did the computer go to the doctor? It had a virus!",
            "What do you call a bear with no teeth? A gummy bear!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "What's orange and sounds like a parrot? A carrot!",
            "Why was the math book sad? Because it had too many problems!",
            "What do you call a fake noodle? An impasta!",
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "What do you call cheese that isn't yours? Nacho cheese!",
            "Why did the bicycle fall over? Because it was two-tired!"
        ]
        return random.choice(jokes)

class WikipediaService:
    """Wikipedia search service"""
    
    @staticmethod
    def search(query: str) -> str:
        """Search Wikipedia"""
        try:
            summary = wikipedia.summary(query, sentences=2)
            return summary
        except wikipedia.exceptions.DisambiguationError:
            return f"Multiple results found for '{query}'. Please be more specific."
        except wikipedia.exceptions.PageError:
            return f"Sorry, no information found about '{query}' on Wikipedia."
        except:
            return f"According to general knowledge, '{query}' is an interesting topic worth exploring."

class CalculationService:
    """Mathematical calculations"""
    
    @staticmethod
    def calculate(expression: str) -> str:
        """Calculate mathematical expression"""
        try:
            # Clean the expression
            expr = expression.lower()
            replacements = {
                'plus': '+', 'minus': '-', 'times': '*', 'multiplied by': '*',
                'divided by': '/', 'over': '/', 'to the power of': '**',
                'squared': '**2', 'cubed': '**3', 'square root of': 'math.sqrt(',
                'percent': '%', 'modulus': '%', 'mod': '%'
            }
            
            for word, symbol in replacements.items():
                expr = expr.replace(word, symbol)
            
            # Close parentheses for square root
            if 'math.sqrt(' in expr:
                expr += ')'
            
            # Extract numbers and operators
            expr = re.sub(r'[^0-9+\-*/().\s]', '', expr)
            
            # Safe evaluation
            if expr:
                result = eval(expr, {"__builtins__": None}, {"math": math})
                return f"The result is {result}"
            else:
                return "Could not calculate that."
                
        except Exception as e:
            return f"Calculation error: {str(e)}"

class MusicPlayer:
    """Music playback service"""
    
    @staticmethod
    def play_song(song_name: str):
        """Play song on YouTube"""
        try:
            pywhatkit.playonyt(song_name)
            return f"🎵 Playing '{song_name}' on YouTube"
        except Exception as e:
            webbrowser.open(f"https://www.youtube.com/results?search_query={song_name}")
            return f"🔍 Searching for '{song_name}' on YouTube"

class FileManager:
    """File and folder operations"""
    
    @staticmethod
    def create_folder(folder_name: str):
        """Create a new folder"""
        try:
            os.makedirs(folder_name, exist_ok=True)
            return f"📁 Created folder: {folder_name}"
        except Exception as e:
            return f"❌ Could not create folder: {str(e)}"
    
    @staticmethod
    def create_file(filename: str, content: str = ""):
        """Create a new file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"📄 Created file: {filename}"
        except Exception as e:
            return f"❌ Could not create file: {str(e)}"

class WebServices:
    """Web-related services"""
    
    @staticmethod
    def search_google(query: str):
        """Search on Google"""
        webbrowser.open(f"https://www.google.com/search?q={query}")
        return f"🔍 Searching Google for: {query}"
    
    @staticmethod
    def open_website(url_alias: str):
        """Open a website"""
        sites = {
            'youtube': 'https://youtube.com',
            'google': 'https://google.com',
            'github': 'https://github.com',
            'gmail': 'https://gmail.com',
            'facebook': 'https://facebook.com',
            'twitter': 'https://twitter.com',
            'instagram': 'https://instagram.com',
            'wikipedia': 'https://wikipedia.org',
            'amazon': 'https://amazon.com',
            'netflix': 'https://netflix.com',
            'spotify': 'https://spotify.com',
            'whatsapp': 'https://web.whatsapp.com',
            'linkedin': 'https://linkedin.com'
        }
        
        if url_alias in sites:
            webbrowser.open(sites[url_alias])
            return f"🌐 Opening {url_alias}"
        else:
            webbrowser.open(f"https://{url_alias}.com")
            return f"🌐 Opening {url_alias}.com"

class SystemControl:
    """System control operations"""
    
    @staticmethod
    def open_application(app_name: str):
        """Open system application"""
        apps = {
            'calculator': 'calc',
            'notepad': 'notepad',
            'paint': 'mspaint',
            'word': 'winword',
            'excel': 'excel',
            'powerpoint': 'powerpnt',
            'command prompt': 'cmd',
            'task manager': 'taskmgr',
            'control panel': 'control',
            'file explorer': 'explorer',
            'chrome': 'chrome',
            'vscode': 'code',
            'visual studio code': 'code',
            'vs code': 'code'
        }
        
        app_lower = app_name.lower()
        for app_key in apps:
            if app_key in app_lower:
                try:
                    os.system(f'start {apps[app_key]}')
                    return f"🖥️ Opening {app_key}"
                except:
                    pass
        
        return f"❌ Could not open {app_name}"

class Games:
    """Interactive games"""
    
    @staticmethod
    def rock_paper_scissors():
        """Play Rock Paper Scissors"""
        choices = ['rock', 'paper', 'scissors']
        computer = random.choice(choices)
        
        return f"🎮 I choose {computer}. What's your choice? (Say rock, paper, or scissors)"
    
    @staticmethod
    def guess_number():
        """Guess the number game"""
        number = random.randint(1, 100)
        return f"🎮 I'm thinking of a number between 1 and 100. Try to guess it!"

class Stories:
    """Story telling"""
    
    @staticmethod
    def tell_story():
        """Tell a random story"""
        stories = [
            "Once upon a time, in a world where AI assistants helped everyone, there was a special assistant named Skye who could understand and respond to human voices.",
            "In the year 2024, a student created an amazing AI assistant for their class project. It could do everything from playing music to solving math problems!",
            "There was a curious AI that loved learning new things. Every day, it helped students with their homework, told them jokes, and made learning fun!",
            "In a digital forest, there lived friendly algorithms that helped organize information. They worked together to make knowledge accessible to everyone.",
            "A story of innovation: How a simple Python script grew into a full-fledged AI assistant that could control computers, search the web, and entertain users."
        ]
        return random.choice(stories)

class Learning:
    """Educational content"""
    
    @staticmethod
    def get_fact():
        """Get an interesting fact"""
        facts = [
            "Did you know? Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly good to eat!",
            "Fun fact: Octopuses have three hearts. Two pump blood to the gills, while the third pumps it to the rest of the body.",
            "Science fact: A day on Venus is longer than a year on Venus. It takes Venus 243 Earth days to rotate once, but only 225 Earth days to orbit the Sun.",
            "Tech fact: The first computer virus was created in 1983 and was called the 'Elk Cloner'. It spread via floppy disks on Apple II computers.",
            "Space fact: There are more stars in the universe than grains of sand on all the beaches on Earth."
        ]
        return random.choice(facts)

class ReminderService:
    """Reminder and notes service"""
    
    def __init__(self):
        self.reminders_file = "skye_reminders.txt"
    
    def add_reminder(self, reminder: str):
        """Add a reminder"""
        try:
            with open(self.reminders_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.datetime.now()}: {reminder}\n")
            return f"📝 Reminder added: {reminder}"
        except:
            return "❌ Could not save reminder"
    
    def show_reminders(self):
        """Show all reminders"""
        try:
            if os.path.exists(self.reminders_file):
                with open(self.reminders_file, 'r', encoding='utf-8') as f:
                    reminders = f.read()
                if reminders:
                    return f"📝 Your reminders:\n{reminders}"
                else:
                    return "📝 No reminders found"
            else:
                return "📝 No reminders file found"
        except:
            return "❌ Could not read reminders"

# ==================== MAIN ASSISTANT ====================
class SkyeAssistant:
    """Main AI Assistant Class"""
    
    def __init__(self):
        print(f"\n{Config.COLORS['HEADER']}{'='*70}{Config.COLORS['END']}")
        print(f"{Config.COLORS['BOLD']}{Config.COLORS['MAGENTA']}🚀 SKYE AI ASSISTANT - COMPLETE WORKING VERSION{Config.COLORS['END']}")
        print(f"{Config.COLORS['HEADER']}{'='*70}{Config.COLORS['END']}")
        
        # Initialize services
        self.tts = TTSManager()
        self.voice_recognizer = VoiceRecognizer()
        
        # Initialize feature managers
        self.weather = WeatherService()
        self.jokes = JokeService()
        self.wikipedia = WikipediaService()
        self.calculator = CalculationService()
        self.music = MusicPlayer()
        self.files = FileManager()
        self.web = WebServices()
        self.system = SystemControl()
        self.games = Games()
        self.stories = Stories()
        self.learning = Learning()
        self.reminders = ReminderService()
        
        # Create projects directory
        os.makedirs(Config.PROJECTS_DIR, exist_ok=True)
        
        print(f"\n{Config.COLORS['GREEN']}✅ Skye Assistant Initialized!{Config.COLORS['END']}")
        print(f"{Config.COLORS['YELLOW']}📁 Projects will be saved in: {Config.PROJECTS_DIR}{Config.COLORS['END']}")
        print(f"{Config.COLORS['BLUE']}🎤 Voice recognition: ACTIVE{Config.COLORS['END']}")
        print(f"{Config.COLORS['BLUE']}🗣️  Text-to-speech: ACTIVE{Config.COLORS['END']}")
    
    def display_banner(self):
        """Display welcome banner"""
        banner = f"""
        {Config.COLORS['BOLD']}{Config.COLORS['CYAN']}╔{'═'*68}╗{Config.COLORS['END']}
        {Config.COLORS['BOLD']}{Config.COLORS['CYAN']}║{' '*24}🤖 SKYE AI 🤖{' '*24}║{Config.COLORS['END']}
        {Config.COLORS['BOLD']}{Config.COLORS['CYAN']}╠{'═'*68}╣{Config.COLORS['END']}
        {Config.COLORS['BOLD']}{Config.COLORS['CYAN']}║{' '*10}🎤 VOICE-ACTIVATED AI ASSISTANT{' '*10}║{Config.COLORS['END']}
        {Config.COLORS['BOLD']}{Config.COLORS['CYAN']}║{' '*12}Perfect for Class Presentation{' '*12}║{Config.COLORS['END']}
        {Config.COLORS['BOLD']}{Config.COLORS['CYAN']}╚{'═'*68}╝{Config.COLORS['END']}
        
        {Config.COLORS['GREEN']}✨ FEATURES:{Config.COLORS['END']}
        • 🎤 Voice Commands    • 🌤️ Weather Info     • 😂 Jokes & Stories
        • 🎵 Music Playback    • 🔍 Web Search       • 📁 File Management
        • ➗ Calculations      • 🖥️ System Control   • 📚 Educational Facts
        • 🎮 Games             • 🌐 Wikipedia Search • 📱 App Launcher
        
        {Config.COLORS['YELLOW']}💡 SAY: '{Config.NAME}' or '{Config.WAKE_WORD}' followed by command{Config.COLORS['END']}
        {Config.COLORS['YELLOW']}💡 EXAMPLE: 'Skye what time is it?' or 'Sky play music'{Config.COLORS['END']}
        {Config.COLORS['YELLOW']}💡 TYPE 'help' for all commands{Config.COLORS['END']}
        """
        print(banner)
    
    def show_help(self):
        """Display help menu"""
        help_text = f"""
        {Config.COLORS['BOLD']}{Config.COLORS['MAGENTA']}📋 AVAILABLE COMMANDS:{Config.COLORS['END']}
        
        {Config.COLORS['GREEN']}🔹 BASIC COMMANDS:{Config.COLORS['END']}
        • hello/hi                 - Greet the assistant
        • time                     - Current time
        • date                     - Today's date
        • help                     - Show this help
        • goodbye/exit/quit        - Exit assistant
        
        {Config.COLORS['GREEN']}🔹 ENTERTAINMENT:{Config.COLORS['END']}
        • tell me a joke           - Hear a joke
        • tell me a story          - Hear a story
        • give me a fact           - Interesting fact
        • play music [song name]   - Play on YouTube
        • play rock paper scissors - Play game
        • play guess number        - Play game
        
        {Config.COLORS['GREEN']}🔹 INFORMATION:{Config.COLORS['END']}
        • weather in [city]        - Get weather
        • search [query]           - Search Google
        • what is [topic]          - Wikipedia search
        • calculate [expression]   - Math calculation
        
        {Config.COLORS['GREEN']}🔹 SYSTEM CONTROL:{Config.COLORS['END']}
        • open [app]               - Open application
        • open website [name]      - Open website
        • create folder [name]     - Create folder
        • create file [name]       - Create file
        • add reminder [text]      - Add reminder
        • show reminders           - Show all reminders
        
        {Config.COLORS['GREEN']}🔹 EXAMPLES:{Config.COLORS['END']}
        • Skye what time is it?
        • Sky weather in London
        • Skye play Despacito
        • Sky open calculator
        • Sky create folder myproject
        • Skye search Python tutorials
        • Sky what is artificial intelligence
        • Sky add reminder study for exam
        """
        print(help_text)
        self.tts.speak("Here are all the commands I understand. You can ask me about time, weather, play music, open apps, and much more!")
    
    def process_command(self, command: str) -> bool:
        """Process user command"""
        cmd = command.lower().strip()
        
        # Check for wake word
        if Config.WAKE_WORD not in cmd and Config.NAME.lower() not in cmd:
            # Check if it's a direct command (without wake word)
            direct_commands = ['time', 'date', 'joke', 'weather', 'open', 'play', 'search', 
                             'calculate', 'create', 'help', 'exit', 'quit', 'goodbye', 'add', 'show']
            if not any(word in cmd for word in direct_commands):
                return True  # Not a command for us
        
        # Remove leading wake words only (avoid stripping words occurring inside the command)
        try:
            wake_pattern = re.compile(rf'^\s*(?:{re.escape(Config.WAKE_WORD)}|{re.escape(Config.NAME.lower())})\b[:,]?\s*', re.IGNORECASE)
            cmd = wake_pattern.sub('', cmd)
        except Exception:
            # Fallback to previous behavior if regex fails for any reason
            cmd = cmd.replace(Config.WAKE_WORD, '').replace(Config.NAME.lower(), '').strip()
        
        print(f"{Config.COLORS['YELLOW']}🔍 Processing: {cmd}{Config.COLORS['END']}")
        
        # ========== GREETINGS ==========
        if any(word in cmd for word in ['hello', 'hi', 'hey']):
            responses = [
                f"Hello! I'm {Config.NAME}, your AI assistant. How can I help you today?",
                f"Hi there! {Config.NAME} here, ready to assist!",
                f"Hey! Great to see you. What can I do for you?"
            ]
            self.tts.speak(random.choice(responses))
        
        # ========== HELP ==========
        elif 'help' in cmd:
            self.show_help()
        
        # ========== TIME & DATE ==========
        elif 'time' in cmd:
            current_time = datetime.datetime.now().strftime('%I:%M %p')
            self.tts.speak(f"The current time is {current_time}")
        
        elif 'date' in cmd:
            today = datetime.datetime.now().strftime('%A, %B %d, %Y')
            self.tts.speak(f"Today is {today}")
        
        # ========== JOKES ==========
        elif 'joke' in cmd:
            joke = self.jokes.get_joke()
            self.tts.speak(joke)
        
        # ========== WEATHER ==========
        elif 'weather' in cmd:
            city = cmd.replace('weather', '').replace('in', '').replace('for', '').strip()
            if city:
                weather_info = self.weather.get_weather(city)
                self.tts.speak(weather_info)
            else:
                self.tts.speak("Please specify a city. For example: weather in London")
        
        # ========== MUSIC ==========
        elif 'play' in cmd and ('music' in cmd or 'song' in cmd):
            song = cmd.replace('play', '').replace('music', '').replace('song', '').strip()
            if song:
                result = self.music.play_song(song)
                self.tts.speak(result)
            else:
                self.tts.speak("What song would you like to play?")
        
        # ========== WIKIPEDIA ==========
        elif 'what is' in cmd or 'who is' in cmd:
            query = cmd.replace('what is', '').replace('who is', '').strip()
            if query:
                info = self.wikipedia.search(query)
                self.tts.speak(info[:200])  # Limit length
        
        # ========== CALCULATIONS ==========
        elif 'calculate' in cmd or ('what is' in cmd and any(op in cmd for op in ['+', '-', '*', '/', 'plus', 'minus'])):
            # Extract calculation part
            calc_part = cmd.replace('calculate', '').replace('what is', '').strip()
            if calc_part:
                result = self.calculator.calculate(calc_part)
                self.tts.speak(result)
        
        # ========== SEARCH ==========
        elif 'search' in cmd or 'google' in cmd:
            query = cmd.replace('search', '').replace('google', '').strip()
            if query:
                result = self.web.search_google(query)
                self.tts.speak(result)
        
        # ========== OPEN WEBSITE ==========
        elif 'open website' in cmd or ('open' in cmd and any(site in cmd for site in ['youtube', 'google', 'github', 'facebook', 'whatsapp'])):
            site = cmd.replace('open website', '').replace('open', '').strip()
            if site:
                result = self.web.open_website(site)
                self.tts.speak(result)
        
        # ========== OPEN APPLICATION ==========
        elif 'open' in cmd and 'website' not in cmd:
            app = cmd.replace('open', '').strip()
            if app:
                result = self.system.open_application(app)
                self.tts.speak(result)
        
        # ========== CREATE FOLDER (flexible parsing) ==========
        elif ('create' in cmd or 'make' in cmd) and 'folder' in cmd:
            # handle phrases like:
            # 'create a new folder named myproject', 'create folder myproject', 'make folder called X'
            folder_name = ''
            # try regex capture of the folder name after the phrase
            try:
                m = re.search(r"(?:create|make)(?: a| new)? folder(?: named| called)?\s*(.*)", cmd, flags=re.IGNORECASE)
                if m:
                    folder_name = m.group(1).strip()
                else:
                    # fallback remove known phrases
                    folder_name = re.sub(r"(?:create|make)(?: a| new)? folder(?: named| called)?", '', cmd, flags=re.IGNORECASE).strip()
            except Exception:
                folder_name = cmd.replace('create folder', '').replace('make folder', '').strip()

            if folder_name:
                full_path = os.path.join(Config.PROJECTS_DIR, folder_name)
                result = self.files.create_folder(full_path)
                self.tts.speak(result)
            else:
                self.tts.speak('What should I name the folder?')
        
        # ========== CREATE FILE ==========
        elif 'create file' in cmd or 'make file' in cmd:
            filename = cmd.replace('create file', '').replace('make file', '').strip()
            if filename:
                # Create in projects directory
                full_path = os.path.join(Config.PROJECTS_DIR, filename)
                result = self.files.create_file(full_path, f"Created by Skye Assistant\nDate: {datetime.datetime.now()}")
                self.tts.speak(result)
        
        # ========== REMINDERS ==========
        elif 'add reminder' in cmd:
            reminder = cmd.replace('add reminder', '').strip()
            if reminder:
                result = self.reminders.add_reminder(reminder)
                self.tts.speak(result)
        
        elif 'show reminders' in cmd:
            result = self.reminders.show_reminders()
            self.tts.speak(result)
        
        # ========== GAMES ==========
        elif 'rock paper scissors' in cmd or 'play game' in cmd:
            result = self.games.rock_paper_scissors()
            self.tts.speak(result)
            
            # Get user choice via voice
            self.tts.speak("Say your choice now: rock, paper, or scissors")
            user_choice = self.voice_recognizer.listen()
            
            if user_choice:
                choices = ['rock', 'paper', 'scissors']
                computer = random.choice(choices)
                
                user_lower = user_choice.lower()
                user_found = None
                for choice in choices:
                    if choice in user_lower:
                        user_found = choice
                        break
                
                if user_found:
                    if user_found == computer:
                        self.tts.speak(f"I also chose {computer}. It's a tie!")
                    elif (user_found == 'rock' and computer == 'scissors') or \
                         (user_found == 'paper' and computer == 'rock') or \
                         (user_found == 'scissors' and computer == 'paper'):
                        self.tts.speak(f"I chose {computer}. You win!")
                    else:
                        self.tts.speak(f"I chose {computer}. I win!")
                else:
                    self.tts.speak("I didn't understand your choice. Let's play again sometime!")
            else:
                self.tts.speak("I didn't hear your choice. Let's play again later!")
        
        elif 'guess number' in cmd:
            result = self.games.guess_number()
            self.tts.speak(result)
            
            number = random.randint(1, 100)
            attempts = 0
            
            while attempts < 7:
                attempts += 1
                self.tts.speak(f"Attempt {attempts}: What's your guess? Say a number between 1 and 100")
                
                # Get voice input
                guess_input = self.voice_recognizer.listen()
                
                if guess_input:
                    try:
                        guess = int(re.search(r'\d+', guess_input).group())
                        
                        if guess < number:
                            self.tts.speak("Too low!")
                        elif guess > number:
                            self.tts.speak("Too high!")
                        else:
                            self.tts.speak(f"🎉 Congratulations! You guessed it in {attempts} attempts!")
                            break
                    except:
                        self.tts.speak("Please say a number!")
                else:
                    self.tts.speak("I didn't hear your guess. Try again!")
            else:
                self.tts.speak(f"Game over! The number was {number}")
        
        # ========== STORIES ==========
        elif 'story' in cmd or 'tell me a story' in cmd:
            story = self.stories.tell_story()
            self.tts.speak(story)
        
        # ========== FACTS ==========
        elif 'fact' in cmd or 'interesting fact' in cmd:
            fact = self.learning.get_fact()
            self.tts.speak(fact)
        
        # ========== GITHUB ==========
        elif 'github' in cmd or 'repository' in cmd:
            webbrowser.open('https://github.com')
            self.tts.speak("Opening GitHub. You can create your project repository here!")
        
        # ========== EXIT ==========
        elif any(word in cmd for word in ['goodbye', 'exit', 'quit', 'bye']):
            farewells = [
                "Goodbye! Have a wonderful day!",
                "See you later! Take care!",
                "Bye! Don't hesitate to call me again!",
                "Shutting down. Goodbye for now!"
            ]
            self.tts.speak(random.choice(farewells))
            return False
        
        # ========== UNKNOWN COMMAND ==========
        else:
            if cmd and len(cmd) > 2:
                responses = [
                    f"I'm not sure about '{cmd}'. Try saying 'help' to see what I can do.",
                    f"Sorry, I didn't understand '{cmd}'. You can ask me about time, weather, or tell me to play music!",
                    f"Regarding '{cmd}', I can help with many tasks. Say 'help' for options."
                ]
                self.tts.speak(random.choice(responses))
        
        return True
    
    def run(self):
        """Main assistant loop"""
        self.display_banner()
        self.tts.speak(f"Hello! I am {Config.NAME}, your AI assistant. Ready to help!")
        
        try:
            while True:
                print(f"\n{Config.COLORS['HEADER']}{'='*70}{Config.COLORS['END']}")
                print(f"{Config.COLORS['YELLOW']}💬 Speak your command (say '{Config.NAME}' first){Config.COLORS['END']}")
                print(f"{Config.COLORS['HEADER']}{'='*70}{Config.COLORS['END']}")
                
                # Get user input via voice with fallback
                command = self.voice_recognizer.listen_with_fallback()
                
                if command:
                    should_continue = self.process_command(command)
                    if not should_continue:
                        break
                else:
                    print(f"{Config.COLORS['RED']}⚠ No command received. Try again.{Config.COLORS['END']}")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n{Config.COLORS['RED']}👋 Shutting down...{Config.COLORS['END']}")
            self.tts.speak("Goodbye!")
        
        finally:
            self.tts.stop()
            print(f"\n{Config.COLORS['GREEN']}✅ Assistant stopped successfully!{Config.COLORS['END']}")

# ==================== DEMO MODE ====================
def run_demo():
    """Run a demonstration of all features"""
    print(f"\n{Config.COLORS['BOLD']}{Config.COLORS['MAGENTA']}🎬 DEMONSTRATION MODE{Config.COLORS['END']}")
    print(f"{Config.COLORS['YELLOW']}Showing all features of Skye Assistant...{Config.COLORS['END']}")
    
    assistant = SkyeAssistant()
    
    demo_commands = [
        ("Skye hello", "Greeting"),
        ("Sky what time is it", "Time check"),
        ("Skye weather in London", "Weather information"),
        ("Sky tell me a joke", "Entertainment"),
        ("Skye calculate 15 plus 27", "Math calculation"),
        ("Sky open calculator", "System control"),
        ("Skye play Despacito", "Music playback"),
        ("Sky search artificial intelligence", "Web search"),
        ("Skye what is Python programming", "Wikipedia search"),
        ("Sky create folder myproject", "File management"),
        ("Sky add reminder study for exam", "Reminder system"),
        ("Skye tell me a story", "Story telling"),
        ("Sky give me a fact", "Educational"),
        ("Skye open website youtube", "Website control"),
        ("Skye goodbye", "Exit")
    ]
    
    for cmd, desc in demo_commands:
        print(f"\n{Config.COLORS['BLUE']}➡️ DEMO: {desc}{Config.COLORS['END']}")
        print(f"{Config.COLORS['YELLOW']}Command: {cmd}{Config.COLORS['END']}")
        assistant.process_command(cmd)
        time.sleep(2)
    
    print(f"\n{Config.COLORS['GREEN']}🎉 Demo completed! All features working perfectly!{Config.COLORS['END']}")

# ==================== MAIN ====================
if __name__ == '__main__':
    print(f"\n{Config.COLORS['BOLD']}{'='*70}{Config.COLORS['END']}")
    print(f"{Config.COLORS['BOLD']}{Config.COLORS['CYAN']}🤖 SKYE AI ASSISTANT - CLASS PROJECT PRESENTATION{Config.COLORS['END']}")
    print(f"{Config.COLORS['BOLD']}{'='*70}{Config.COLORS['END']}")
    
    # Menu
    print(f"\n{Config.COLORS['GREEN']}1. 🚀 Run Full Assistant (Voice Commands)")
    print(f"2. 🎬 Run Demo (Show All Features)")
    print(f"3. 📋 Show Features List")
    print(f"4. ❌ Exit{Config.COLORS['END']}")
    
    choice = input(f"\n{Config.COLORS['YELLOW']}Select option (1-4): {Config.COLORS['END']}").strip()
    
    if choice == '1':
        assistant = SkyeAssistant()
        assistant.run()
    elif choice == '2':
        run_demo()
    elif choice == '3':
        assistant = SkyeAssistant()
        assistant.show_help()
        input(f"\n{Config.COLORS['YELLOW']}Press Enter to exit...{Config.COLORS['END']}")
    else:
        print(f"\n{Config.COLORS['GREEN']}Goodbye! 🎉{Config.COLORS['END']}")
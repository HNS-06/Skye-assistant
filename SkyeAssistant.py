"""
SKYE AI ASSISTANT - WORKING VOICE VERSION
Using Windows Speech API (reliable)
"""

import os
import time
import threading
import sqlite3
import webbrowser
import requests
import random
import traceback
import re
from datetime import datetime, timedelta

# Import speech recognition
import speech_recognition as sr

# For TTS - Use Windows Speech API which is more reliable
try:
    import win32com.client
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("⚠ Windows Speech API not available. Install pywin32: pip install pywin32")

# Other imports
import pywhatkit
import pyjokes
import wikipedia
from dotenv import load_dotenv
import pygame

# Load environment variables
load_dotenv()

# ==================== CONFIG ====================
class Config:
    ASSISTANT_NAME = os.getenv('ASSISTANT_NAME', 'Skye')
    MUSIC_DIR = os.path.join(os.path.expanduser('~'), 'Music')
    VOICE_RATE = 0  # Windows Speech rate (-10 to 10, 0 is normal)
    VOICE_VOLUME = 100  # Windows Speech volume (0-100)


# ==================== RELIABLE WINDOWS TTS ====================
class WindowsTTS:
    """Reliable TTS using Windows Speech API"""
    def __init__(self):
        self.speaker = None
        self._init_speaker()
    
    def _init_speaker(self):
        """Initialize Windows Speech API"""
        try:
            if TTS_AVAILABLE:
                self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
                
                # Get available voices
                voices = self.speaker.GetVoices()
                
                # Try to find a female voice (Zira or Hazel)
                for i in range(voices.Count):
                    voice = voices.Item(i)
                    voice_name = voice.GetDescription()
                    if 'Zira' in voice_name or 'Hazel' in voice_name or 'Female' in voice_name:
                        self.speaker.Voice = voice
                        print(f"✅ Selected voice: {voice_name}")
                        break
                
                # Set rate and volume
                self.speaker.Rate = Config.VOICE_RATE
                self.speaker.Volume = Config.VOICE_VOLUME
                
                # Test voice
                self.speaker.Speak(" ")
                print("✅ Windows TTS initialized successfully")
            else:
                print("⚠ Windows TTS not available")
                self.speaker = None
                
        except Exception as e:
            print(f"❌ TTS initialization failed: {e}")
            self.speaker = None
    
    def speak(self, text):
        """Speak text using Windows Speech API"""
        if not text:
            return
        
        print(f"🗣️ Speaking: {text[:60]}...")
        
        if self.speaker:
            try:
                # Speak asynchronously
                self.speaker.Speak(text, 1)  # 1 = async flag
            except Exception as e:
                print(f"❌ Speech error: {e}")
                # Try synchronous as fallback
                try:
                    self.speaker.Speak(text)
                except:
                    print(f"[TEXT]: {text}")
        else:
            print(f"[VOICE]: {text}")
    
    def wait_until_done(self, timeout=5):
        """Wait for speech to complete"""
        if self.speaker:
            # Windows Speech API doesn't have a direct way to check
            # We'll just wait a bit based on text length
            time.sleep(min(len(text) * 0.1, timeout))
    
    def stop(self):
        """Stop any ongoing speech"""
        if self.speaker:
            try:
                self.speaker.Speak("", 2)  # 2 = purge flag
            except:
                pass


# ==================== MAIN ASSISTANT CLASS ====================
class SkyeAssistant:
    def __init__(self):
        print("=" * 60)
        print("🚀 INITIALIZING SKYE ASSISTANT")
        print("=" * 60)
        
        # Initialize TTS
        self.tts = WindowsTTS()
        time.sleep(0.5)
        
        # Initialize audio
        pygame.mixer.init()
        print("✅ Audio mixer initialized")
        
        # Initialize database
        self._setup_db()
        
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        print("✅ Speech recognizer initialized")
        
        self.last_command_time = time.time()
        
        print("✅ Skye Assistant initialized successfully!")
        print("=" * 60)
    
    def _setup_db(self):
        """Setup database"""
        try:
            self.db_conn = sqlite3.connect('skye_assistant.db', check_same_thread=False)
            cur = self.db_conn.cursor()
            
            # Create reminders table
            cur.execute('''CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY, 
                reminder TEXT, 
                reminder_time TEXT, 
                created_at TEXT, 
                is_completed INTEGER DEFAULT 0
            )''')
            
            self.db_conn.commit()
            print("✅ Database initialized")
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            self.db_conn = sqlite3.connect(':memory:', check_same_thread=False)
    
    def _play_chime(self):
        """Play a simple beep sound"""
        try:
            # Create a simple beep
            sample_rate = 22050
            duration = 0.1
            frequency = 800
            
            import numpy as np
            samples = (np.sin(2 * np.pi * np.arange(sample_rate * duration) * frequency / sample_rate)).astype(np.float32)
            
            import sounddevice as sd
            sd.play(samples, sample_rate)
            sd.wait()
        except:
            # Fallback: system beep
            print('\a', end='', flush=True)
    
    # ========== SPEECH FUNCTIONS ==========
    
    def listen(self, timeout=5, phrase_time_limit=7):
        """Listen for user speech"""
        try:
            with sr.Microphone() as source:
                print("\n🎤 LISTENING... (speak now)")
                
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Listen
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
                
                # Recognize
                text = self.recognizer.recognize_google(audio)
                print(f"👤 YOU SAID: {text}")
                self.last_command_time = time.time()
                return text.lower()
                
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            print("⚠ Could not understand audio")
            return ""
        except sr.RequestError as e:
            print(f"❌ Speech service error: {e}")
            return ""
        except Exception as e:
            print(f"❌ Listen error: {e}")
            return ""
    
    def speak_response(self, text):
        """Speak a response"""
        if not text:
            return
        
        # Play chime
        self._play_chime()
        time.sleep(0.1)
        
        # Speak
        self.tts.speak(text)
        time.sleep(0.3)  # Brief pause after speaking
    
    # ========== CORE FEATURES ==========
    
    def tell_joke(self):
        """Tell a joke"""
        try:
            joke = pyjokes.get_joke()
        except:
            joke = "Why did the computer go to the doctor? It had a virus!"
        
        print(f"😂 {joke}")
        self.speak_response(joke)
    
    def get_time(self):
        """Get current time"""
        now = datetime.now().strftime('%I:%M %p')
        response = f"The time is {now}"
        print(f"🕒 {response}")
        self.speak_response(response)
    
    def get_date(self):
        """Get current date"""
        today = datetime.now().strftime('%B %d, %Y')
        response = f"Today is {today}"
        print(f"📅 {response}")
        self.speak_response(response)
    
    def play_music(self):
        """Play music"""
        self.speak_response("What song would you like to play?")
        
        response = self.listen(timeout=8)
        
        if not response:
            self.speak_response("I didn't hear a song name.")
            return
        
        if 'local' in response or 'offline' in response:
            self.speak_response("Opening your Music folder...")
            music_folder = os.path.join(os.path.expanduser('~'), 'Music')
            if os.path.exists(music_folder):
                os.startfile(music_folder)
            else:
                self.speak_response("Music folder not found.")
        else:
            song_name = response.replace('play', '').strip()
            response = f'Playing {song_name} on YouTube'
            print(f"🎵 {response}")
            self.speak_response(response)
            
            try:
                pywhatkit.playonyt(song_name)
            except:
                webbrowser.open(f'https://www.youtube.com/results?search_query={song_name}')
    
    def search_web(self, query=None):
        """Search the web"""
        if not query:
            self.speak_response("What would you like to search for?")
            query = self.listen()
        
        if query:
            response = f'Searching for {query}'
            print(f"🔍 {response}")
            self.speak_response(response)
            webbrowser.open(f'https://www.google.com/search?q={query}')
    
    def get_weather(self, location=None):
        """Get weather"""
        if not location:
            self.speak_response("For which city?")
            location = self.listen()
        
        if not location:
            return
        
        # Simple weather responses
        weather_responses = {
            'new york': "Partly cloudy, 22°C",
            'london': "Rainy, 15°C", 
            'paris': "Sunny, 20°C",
            'tokyo': "Clear, 25°C",
            'delhi': "Hot, 35°C",
            'mumbai': "Humid, 30°C",
            'los angeles': "Sunny, 28°C",
            'chicago': "Windy, 18°C",
            'kochi': "Warm and humid, 28°C with possible rain",
            'chennai': "Hot and humid, 32°C",
            'bangalore': "Pleasant, 26°C"
        }
        
        location_key = location.lower()
        
        for city in weather_responses:
            if city in location_key:
                response = f"Weather in {city.title()}: {weather_responses[city]}"
                print(f"☁️ {response}")
                self.speak_response(response)
                return
        
        # If location not found, use Open-Meteo API
        try:
            # Try to get coordinates for the city
            cities_coords = {
                'kochi': (9.9312, 76.2673),
                'chennai': (13.0827, 80.2707),
                'bangalore': (12.9716, 77.5946),
                'delhi': (28.6139, 77.2090),
                'mumbai': (19.0760, 72.8777)
            }
            
            for city, coords in cities_coords.items():
                if city in location_key:
                    lat, lon = coords
                    url = f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true'
                    r = requests.get(url, timeout=5)
                    data = r.json()
                    
                    if 'current_weather' in data:
                        temp = data['current_weather']['temperature']
                        response = f"Current temperature in {city.title()}: {temp}°C"
                        print(f"☁️ {response}")
                        self.speak_response(response)
                        return
        except:
            pass
        
        self.speak_response(f"I don't have weather data for {location}. Try major cities like New York or London.")
    
    def wikipedia_search(self, query=None):
        """Search Wikipedia"""
        if not query:
            self.speak_response("What would you like to know about?")
            query = self.listen()
        
        if query:
            try:
                summary = wikipedia.summary(query, sentences=2)
                print(f"📚 {summary[:100]}...")
                self.speak_response(summary[:150])  # Limit speech length
            except:
                self.speak_response(f"Sorry, I couldn't find information about {query}")
    
    def set_reminder(self):
        """Set a reminder"""
        self.speak_response("What should I remind you about?")
        text = self.listen()
        
        if not text:
            self.speak_response("I didn't hear the reminder text.")
            return
        
        self.speak_response("In how many minutes? Say a number.")
        when = self.listen()
        
        # Default: 5 minutes
        minutes = 5
        
        if when:
            numbers = re.findall(r'\d+', when)
            if numbers:
                minutes = int(numbers[0])
        
        reminder_time = datetime.now() + timedelta(minutes=minutes)
        
        try:
            cur = self.db_conn.cursor()
            cur.execute(
                'INSERT INTO reminders (reminder, reminder_time, created_at) VALUES (?, ?, ?)',
                (text, reminder_time.isoformat(), datetime.now().isoformat())
            )
            self.db_conn.commit()
            
            response = f'Reminder set for {minutes} minutes from now: {text}'
            print(f"⏰ {response}")
            self.speak_response(f"Reminder set for {minutes} minutes")
            
        except Exception as e:
            print(f"❌ Reminder error: {e}")
            self.speak_response("Sorry, couldn't set the reminder.")
    
    def open_application(self, app_name):
        """Open application"""
        apps = {
            'chrome': 'chrome',
            'notepad': 'notepad',
            'calculator': 'calc',
            'paint': 'mspaint',
            'word': 'winword',
            'excel': 'excel',
            'powerpoint': 'powerpnt',
            'command': 'cmd',
            'explorer': 'explorer'
        }
        
        for app_key, command in apps.items():
            if app_key in app_name.lower():
                try:
                    os.system(f'start {command}')
                    response = f'Opening {app_key}'
                    print(f"📱 {response}")
                    self.speak_response(response)
                    return
                except:
                    break
        
        self.speak_response(f"I couldn't find {app_name} to open")
    
    def get_news(self):
        """Get news headlines"""
        self.speak_response("Here are today's top headlines...")
        
        # Simple headlines
        headlines = [
            "Technology companies announce new AI developments",
            "Scientists discover potential breakthrough in renewable energy",
            "Global markets show steady growth this quarter",
            "Space exploration reaches new milestones",
            "Healthcare innovations improve treatment options"
        ]
        
        for i, headline in enumerate(headlines[:3], 1):
            print(f"📰 {i}. {headline}")
            self.speak_response(f"Headline {i}: {headline}")
            time.sleep(1)
    
    def solve_math(self, problem):
        """Solve math problems"""
        print(f"🧮 Problem: {problem}")
        self.speak_response("Let me calculate that...")
        
        try:
            # Extract numbers
            numbers = re.findall(r'\d+', problem)
            
            if len(numbers) >= 2:
                a, b = int(numbers[0]), int(numbers[1])
                
                if 'plus' in problem or '+' in problem or 'add' in problem:
                    result = a + b
                    response = f"{a} plus {b} equals {result}"
                elif 'minus' in problem or '-' in problem or 'subtract' in problem:
                    result = a - b
                    response = f"{a} minus {b} equals {result}"
                elif 'times' in problem or 'multiply' in problem or 'x' in problem:
                    result = a * b
                    response = f"{a} times {b} equals {result}"
                elif 'divide' in problem or '/' in problem:
                    if b != 0:
                        result = a / b
                        response = f"{a} divided by {b} equals {result:.2f}"
                    else:
                        response = "Cannot divide by zero"
                else:
                    response = f"I found numbers {a} and {b}. What operation should I perform?"
            else:
                response = "I need at least two numbers to perform a calculation."
            
            print(f"✅ {response}")
            self.speak_response(response)
            
        except Exception as e:
            print(f"❌ Math error: {e}")
            self.speak_response("Sorry, I couldn't solve that math problem.")
    
    def rock_paper_scissors(self):
        """Play Rock Paper Scissors"""
        self.speak_response("Let's play! Say rock, paper, or scissors when I ask.")
        time.sleep(1)
        
        choices = ['rock', 'paper', 'scissors']
        computer = random.choice(choices)
        
        self.speak_response("Ready? Rock, paper, scissors...")
        time.sleep(0.5)
        self.speak_response("What's your choice?")
        
        player_choice = self.listen()
        
        if not player_choice:
            self.speak_response("I didn't hear your choice. Let's try again.")
            return
        
        player = None
        for choice in choices:
            if choice in player_choice.lower():
                player = choice
                break
        
        if not player:
            self.speak_response("Please say rock, paper, or scissors.")
            return
        
        self.speak_response(f"I chose {computer}")
        time.sleep(1)
        
        if player == computer:
            self.speak_response("It's a tie!")
        elif (player == 'rock' and computer == 'scissors') or \
             (player == 'paper' and computer == 'rock') or \
             (player == 'scissors' and computer == 'paper'):
            self.speak_response("You win!")
        else:
            self.speak_response("I win!")
    
    def guided_breathing(self):
        """Guided breathing exercise"""
        self.speak_response("Let's do a short breathing exercise. Follow my instructions.")
        time.sleep(2)
        
        self.speak_response("Breathe in slowly...")
        time.sleep(4)
        
        self.speak_response("Hold your breath...")
        time.sleep(4)
        
        self.speak_response("Breathe out slowly...")
        time.sleep(4)
        
        self.speak_response("Good! Let's do one more round.")
        time.sleep(1)
        
        self.speak_response("Breathe in...")
        time.sleep(4)
        
        self.speak_response("Hold...")
        time.sleep(4)
        
        self.speak_response("Breathe out...")
        time.sleep(4)
        
        self.speak_response("Excellent! You should feel more relaxed now.")
    
    def tell_story(self):
        """Tell a story"""
        stories = [
            "Once upon a time, there was a friendly AI assistant named Skye who loved helping people with their daily tasks.",
            "In a digital world, humans and artificial intelligence worked together to solve problems and create wonderful things.",
            "There was a curious programmer who built an assistant that could understand voices and bring joy to everyone it helped."
        ]
        
        story = random.choice(stories)
        print(f"📖 {story}")
        self.speak_response(story)
    
    def daily_tip(self):
        """Give a daily tip"""
        tips = [
            "Remember to take short breaks to stay focused and productive.",
            "Drinking enough water is essential for both your body and mind.",
            "Practicing gratitude each day can improve your overall happiness.",
            "Getting enough sleep helps your brain function at its best.",
            "Regular exercise, even a short walk, can boost your energy levels."
        ]
        
        tip = random.choice(tips)
        print(f"💡 {tip}")
        self.speak_response(tip)
    
    # ========== COMMAND PROCESSING ==========
    
    def process_command(self, command):
        """Process user commands"""
        if not command:
            return 'continue'
        
        cmd = command.lower()
        
        # Remove assistant name
        cmd = cmd.replace(Config.ASSISTANT_NAME.lower(), '').strip()
        
        print(f"🔍 Processing: {cmd}")
        
        # Greetings
        if any(word in cmd for word in ['hello', 'hi', 'hey']):
            responses = [
                f"Hello! I'm {Config.ASSISTANT_NAME}. How can I help you today?",
                f"Hi there! Nice to hear from you!",
                f"Hey! {Config.ASSISTANT_NAME} here. What can I do for you?"
            ]
            self.speak_response(random.choice(responses))
        
        # How are you
        elif 'how are you' in cmd:
            responses = [
                "I'm doing great, thank you for asking!",
                "I'm excellent and ready to help!",
                "I'm wonderful! How can I assist you today?"
            ]
            self.speak_response(random.choice(responses))
        
        # Time
        elif 'time' in cmd:
            self.get_time()
        
        # Date
        elif 'date' in cmd:
            self.get_date()
        
        # Joke
        elif 'joke' in cmd:
            self.tell_joke()
        
        # Weather
        elif 'weather' in cmd:
            location = cmd.replace('weather', '').replace('in', '').replace('for', '').replace('the', '').strip()
            self.get_weather(location if location else None)
        
        # Music
        elif 'play' in cmd and ('music' in cmd or 'song' in cmd):
            self.play_music()
        elif cmd.startswith('play '):
            song = cmd[5:].strip()
            if song:
                response = f'Playing {song} on YouTube'
                print(f"🎵 {response}")
                self.speak_response(response)
                webbrowser.open(f'https://www.youtube.com/results?search_query={song}')
        
        # Search
        elif 'search' in cmd or 'google' in cmd:
            query = cmd.replace('search', '').replace('google', '').strip()
            self.search_web(query if query else None)
        
        # Wikipedia
        elif 'who is' in cmd or 'what is' in cmd:
            query = cmd.replace('who is', '').replace('what is', '').strip()
            self.wikipedia_search(query if query else None)
        
        # Math
        elif any(word in cmd for word in ['calculate', 'solve', 'math']):
            self.solve_math(cmd)
        
        # Reminder
        elif 'remind' in cmd:
            self.set_reminder()
        
        # Open app
        elif cmd.startswith('open '):
            app = cmd[5:].strip()
            self.open_application(app)
        
        # News
        elif 'news' in cmd or 'headlines' in cmd:
            self.get_news()
        
        # Activities
        elif 'rock' in cmd or 'paper' in cmd or 'scissors' in cmd:
            self.rock_paper_scissors()
        elif 'breathe' in cmd or 'breathing' in cmd:
            self.guided_breathing()
        elif 'story' in cmd:
            self.tell_story()
        elif 'tip' in cmd:
            self.daily_tip()
        elif 'quiz' in cmd or 'trivia' in cmd:
            self.speak_response("Quiz feature coming soon!")
        
        # Help
        elif 'help' in cmd or 'what can you do' in cmd:
            help_text = "I can tell jokes, play music, check weather, set reminders, tell time, search web, open apps, give news, solve math problems, play games, and more!"
            self.speak_response(help_text)
        
        # Exit
        elif any(word in cmd for word in ['exit', 'quit', 'goodbye', 'stop', 'bye']):
            farewells = [
                "Goodbye! Have a wonderful day!",
                "See you later! Take care!",
                "Bye! Don't hesitate to call me again!"
            ]
            self.speak_response(random.choice(farewells))
            return 'exit'
        
        # Unknown command
        else:
            if len(cmd) > 2:
                responses = [
                    f"I heard you say: {command}. How can I help with that?",
                    "I'm not sure about that. Try asking me to play music, tell a joke, or check the weather.",
                    f"Regarding {command}, I can help with various tasks. Say 'help' to see what I can do."
                ]
                self.speak_response(random.choice(responses))
        
        return 'continue'
    
    # ========== MAIN LOOP ==========
    
    def run(self):
        """Main assistant loop"""
        # Welcome
        welcome = f"Hello! I am {Config.ASSISTANT_NAME}, your voice assistant."
        print(f"\n🗣️ {welcome}")
        self.speak_response(welcome)
        
        time.sleep(0.5)
        
        help_msg = "I'm ready to help. Say 'help' to know what I can do."
        print(f"💡 {help_msg}")
        self.speak_response(help_msg)
        
        # Main loop
        while True:
            try:
                print(f"\n{'='*40}")
                print(f"🎤 Say something... (or '{Config.ASSISTANT_NAME}' to activate)")
                print(f"{'='*40}")
                
                command = self.listen(timeout=6)
                
                if command:
                    result = self.process_command(command)
                    if result == 'exit':
                        break
                else:
                    # Check idle time
                    if time.time() - self.last_command_time > 30:
                        self.speak_response("I'm here if you need anything.")
                        self.last_command_time = time.time()
                
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print("\n\n👋 Shutting down...")
                self.speak_response("Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                traceback.print_exc()
                time.sleep(1)
        
        self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        print("\n🧹 Cleaning up...")
        try:
            self.db_conn.close()
        except:
            pass
        
        try:
            self.tts.stop()
        except:
            pass
        
        print("✅ Cleanup complete")


# ========== MAIN ==========
if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("          SKYE AI ASSISTANT - WINDOWS SPEECH")
    print("=" * 60)
    
    # First install check
    if not TTS_AVAILABLE:
        print("\n⚠ IMPORTANT: Windows Speech API not available!")
        print("Install required package: pip install pywin32")
        choice = input("\nContinue without voice? (y/n): ").lower()
        if choice != 'y':
            exit()
    
    # Create and run assistant
    assistant = SkyeAssistant()
    
    try:
        assistant.run()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        assistant.cleanup()
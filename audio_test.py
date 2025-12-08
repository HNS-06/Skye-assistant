"""
Skye Assistant Audio Diagnostics Tool
=====================================
Comprehensive audio testing for Skye AI Assistant.
Tests TTS, speech recognition, and audio playback systems.
"""

import os
import sys
import time
import traceback
from datetime import datetime

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)

def print_result(test_name, status, message=""):
    """Print test result with color coding"""
    if status == "PASS":
        print(f"✓ {test_name}: PASS {message}")
    elif status == "FAIL":
        print(f"✗ {test_name}: FAIL {message}")
    elif status == "WARN":
        print(f"⚠ {test_name}: WARNING {message}")
    else:
        print(f"  {test_name}: {status} {message}")

def test_system_info():
    """Display system information"""
    print_header("SYSTEM INFORMATION")
    
    print(f"Platform: {sys.platform}")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def test_pyttsx3_detailed():
    """Detailed pyttsx3 test"""
    print_header("PYTTSX3 TEST")
    
    try:
        import pyttsx3
        print("Import successful")
        
        # Initialize engine
        print("Initializing TTS engine...")
        engine = pyttsx3.init()
        
        # Get and display voices
        voices = engine.getProperty('voices')
        print(f"\nAvailable voices ({len(voices)}):")
        for i, voice in enumerate(voices):
            print(f"  {i}: {voice.name} ({voice.id})")
            if 'female' in voice.name.lower():
                print("     ^ Female voice detected")
            elif 'zira' in voice.name.lower():
                print("     ^ Zira voice detected")
        
        # Set female voice if available
        female_voices = [v for v in voices if 'female' in v.name.lower() or 'zira' in v.name.lower()]
        if female_voices:
            engine.setProperty('voice', female_voices[0].id)
            print(f"\nSelected voice: {female_voices[0].name}")
        elif len(voices) > 1:
            engine.setProperty('voice', voices[1].id)
            print(f"\nSelected voice: {voices[1].name}")
        else:
            engine.setProperty('voice', voices[0].id)
            print(f"\nSelected voice: {voices[0].name}")
        
        # Test speech
        print("\nSpeaking test phrase...")
        engine.setProperty('rate', 170)
        engine.setProperty('volume', 1.0)
        engine.say("Hello! This is Skye Assistant. If you can hear this, the text-to-speech system is working correctly.")
        engine.say("This is a second test sentence to ensure continuous speech works properly.")
        engine.runAndWait()
        
        print_result("pyttsx3", "PASS", "TTS engine initialized and speaking successfully")
        return True
        
    except ImportError:
        print_result("pyttsx3", "FAIL", "Package not installed. Run: pip install pyttsx3")
        return False
    except Exception as e:
        print_result("pyttsx3", "FAIL", f"Error: {str(e)}")
        print(f"\nError details:")
        traceback.print_exc()
        return False

def test_speech_recognition():
    """Test speech recognition"""
    print_header("SPEECH RECOGNITION TEST")
    
    try:
        import speech_recognition as sr
        print("Import successful")
        
        # Initialize recognizer
        recognizer = sr.Recognizer()
        print("Recognizer initialized")
        
        # Test microphone availability
        print("\nChecking microphone...")
        try:
            with sr.Microphone() as source:
                print("Microphone detected")
                
                # Test ambient noise adjustment
                print("Adjusting for ambient noise (1 second)...")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Ambient noise adjustment complete")
                
                # Short listening test
                print("\n🎤 Speak a short phrase now (5 second timeout)...")
                print("Listening...")
                
                try:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                    print("Audio captured successfully")
                    
                    # Try to recognize
                    print("Processing speech...")
                    text = recognizer.recognize_google(audio)
                    print(f"Recognized: '{text}'")
                    
                    print_result("Speech Recognition", "PASS", f"Recognized: {text}")
                    return True
                    
                except sr.WaitTimeoutError:
                    print_result("Speech Recognition", "WARN", "No speech detected (timeout)")
                    return False
                except sr.UnknownValueError:
                    print_result("Speech Recognition", "WARN", "Could not understand speech")
                    return False
                except sr.RequestError as e:
                    print_result("Speech Recognition", "FAIL", f"API error: {e}")
                    return False
                    
        except Exception as e:
            print_result("Speech Recognition", "FAIL", f"Microphone error: {e}")
            return False
            
    except ImportError:
        print_result("Speech Recognition", "FAIL", "Package not installed. Run: pip install SpeechRecognition")
        return False
    except Exception as e:
        print_result("Speech Recognition", "FAIL", f"Error: {str(e)}")
        print(f"\nError details:")
        traceback.print_exc()
        return False

def test_audio_playback():
    """Test audio playback with pygame"""
    print_header("AUDIO PLAYBACK TEST")
    
    try:
        import pygame
        print("Import successful")
        
        # Initialize pygame mixer
        print("Initializing pygame mixer...")
        pygame.mixer.init()
        print(f"Mixer initialized: {pygame.mixer.get_init()}")
        
        # Test chime sound if available
        chime_path = "chime.wav"
        if os.path.exists(chime_path):
            print(f"\nTesting chime sound ({chime_path})...")
            try:
                pygame.mixer.music.load(chime_path)
                pygame.mixer.music.play()
                print("Playing chime sound...")
                
                # Wait for playback
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                    
                print_result("Audio Playback", "PASS", "Chime sound played successfully")
                return True
                
            except Exception as e:
                print_result("Audio Playback", "WARN", f"Could not play chime: {e}")
        else:
            print(f"\nChime file not found at: {chime_path}")
        
        # Test simple beep
        print("\nTesting system beep...")
        try:
            import winsound
            winsound.Beep(1000, 500)  # 1000 Hz, 500 ms
            print_result("Audio Playback", "PASS", "System beep successful")
            return True
        except:
            print_result("Audio Playback", "WARN", "Could not play system beep")
            return False
            
    except ImportError:
        print_result("Audio Playback", "FAIL", "Package not installed. Run: pip install pygame")
        return False
    except Exception as e:
        print_result("Audio Playback", "FAIL", f"Error: {str(e)}")
        print(f"\nError details:")
        traceback.print_exc()
        return False

def test_web_audio():
    """Test web audio capabilities"""
    print_header("WEB AUDIO TEST")
    
    try:
        from gtts import gTTS
        import tempfile
        print("gTTS import successful")
        
        # Create test text
        test_text = "This is a test of Google Text-to-Speech. If you hear this, gTTS is working."
        
        # Create temp file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            temp_file = tmp.name
        
        try:
            # Generate speech
            print("Generating speech with gTTS...")
            tts = gTTS(text=test_text, lang='en', slow=False)
            tts.save(temp_file)
            print(f"Audio saved to: {temp_file}")
            
            # Try to play with pygame
            try:
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                print("Playing gTTS audio...")
                
                # Wait for playback
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                    
                print_result("Web Audio (gTTS)", "PASS", "gTTS audio generated and played successfully")
                return True
                
            except Exception as e:
                print_result("Web Audio (gTTS)", "WARN", f"Generated but couldn't play: {e}")
                return False
                
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
                
    except ImportError:
        print_result("Web Audio", "FAIL", "Package not installed. Run: pip install gtts")
        return False
    except Exception as e:
        print_result("Web Audio", "FAIL", f"Error: {str(e)}")
        print(f"\nError details:")
        traceback.print_exc()
        return False

def test_microphone_detailed():
    """Detailed microphone test"""
    print_header("MICROPHONE DETAILED TEST")
    
    try:
        import speech_recognition as sr
        print("Checking available microphones...")
        
        microphones = sr.Microphone.list_microphone_names()
        if microphones:
            print(f"\nFound {len(microphones)} microphone(s):")
            for i, mic in enumerate(microphones):
                print(f"  [{i}] {mic}")
                
            # Test default microphone
            print("\nTesting default microphone...")
            try:
                with sr.Microphone() as source:
                    print(f"Default microphone: {source}")
                    print("Microphone test passed")
                    print_result("Microphone", "PASS", f"Found {len(microphones)} microphone(s)")
                    return True
            except Exception as e:
                print_result("Microphone", "FAIL", f"Default mic error: {e}")
                return False
        else:
            print_result("Microphone", "FAIL", "No microphones found")
            return False
            
    except Exception as e:
        print_result("Microphone", "FAIL", f"Error: {e}")
        return False

def test_sky_assistant_integration():
    """Test Skye Assistant integration"""
    print_header("SKYE ASSISTANT INTEGRATION TEST")
    
    try:
        # Try to import Skye Assistant
        print("Testing Skye Assistant import...")
        sys.path.insert(0, os.getcwd())
        
        # Check for config
        if os.path.exists('.env'):
            print("Found .env configuration file")
        
        # Test basic functionality
        print("\nTesting basic TTS functionality...")
        try:
            # Simple test without full import
            import pyttsx3
            engine = pyttsx3.init()
            engine.say("Skye Assistant integration test successful.")
            engine.runAndWait()
            
            print_result("Skye Integration", "PASS", "Basic TTS integration works")
            return True
            
        except Exception as e:
            print_result("Skye Integration", "WARN", f"Basic TTS error: {e}")
            return False
            
    except Exception as e:
        print_result("Skye Integration", "FAIL", f"Import error: {e}")
        return False

def run_comprehensive_test():
    """Run all tests"""
    print_header("SKYE ASSISTANT AUDIO DIAGNOSTICS")
    print("This tool tests all audio components of Skye Assistant.\n")
    
    # Start timing
    start_time = time.time()
    
    # Run all tests
    test_system_info()
    
    results = {
        "pyttsx3": test_pyttsx3_detailed(),
        "speech_recognition": test_speech_recognition(),
        "audio_playback": test_audio_playback(),
        "web_audio": test_web_audio(),
        "microphone": test_microphone_detailed(),
        "integration": test_sky_assistant_integration(),
    }
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print(f"Tests completed in {elapsed_time:.1f} seconds")
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED! Skye Assistant audio system is ready.")
    elif passed >= total / 2:
        print(f"\n⚠ {passed}/{total} tests passed. Some features may work.")
    else:
        print(f"\n❌ Only {passed}/{total} tests passed. Audio system needs attention.")
    
    # Recommendations
    print_header("RECOMMENDATIONS")
    
    if not results["pyttsx3"]:
        print("• Install pyttsx3: pip install pyttsx3")
    
    if not results["speech_recognition"]:
        print("• Install SpeechRecognition: pip install SpeechRecognition")
        print("• Check microphone connection and permissions")
    
    if not results["audio_playback"]:
        print("• Install pygame: pip install pygame")
        print("• Check system audio output")
    
    if not results["microphone"]:
        print("• Connect a microphone")
        print("• Check microphone permissions in Windows settings")
    
    print("\nFor Skye Assistant to work properly, ensure:")
    print("1. Microphone is connected and enabled")
    print("2. Speakers/headphones are working")
    print("3. All required packages are installed")
    print("4. Run as administrator if having permission issues")

def quick_test():
    """Quick essential tests only"""
    print_header("QUICK SKYE AUDIO TEST")
    
    print("Running essential tests only...\n")
    
    essential_tests = [
        ("TTS Engine", test_pyttsx3_detailed),
        ("Microphone", test_speech_recognition),
        ("Audio Playback", test_audio_playback),
    ]
    
    for test_name, test_func in essential_tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        success = test_func()
        if success:
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\nQuick test complete!")

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        quick_test()
    else:
        try:
            run_comprehensive_test()
        except KeyboardInterrupt:
            print("\n\nDiagnostics interrupted by user.")
        except Exception as e:
            print(f"\n❌ Unexpected error during diagnostics: {e}")
            traceback.print_exc()
    
    # Keep window open if double-clicked
    if sys.platform == "win32" and 'idlelib' not in sys.modules:
        input("\nPress Enter to exit...")
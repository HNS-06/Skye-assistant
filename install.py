# Create a new file called install.py with this content:
import subprocess
import sys

packages = [
    "SpeechRecognition==3.10.0",
    "pyttsx3==2.90",
    "pywhatkit==5.4",
    "pyjokes==0.6.0",
    "wikipedia==1.4.0",
    "requests==2.31.0"
]

print("Installing required packages...")
for package in packages:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Installed: {package}")
    except:
        print(f"⚠ Could not install: {package}")

print("\n✅ Installation complete! Now run: python SkyeAssistant.py")
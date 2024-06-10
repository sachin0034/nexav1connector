import requests
import os
from flask import current_app
from werkzeug.utils import secure_filename
import sqlite3

# Function to get the database path
def get_db_path():
    return os.path.join(os.path.dirname(__file__), '../data/config.db')

def init_db():
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)  # Ensure the directory exists
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS config
                      (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit()
    conn.close()
     # Set read and write permissions for the database file
    os.chmod(db_path, 0o666)  # rw-rw-rw-

def get_key(key):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Initialize the database
init_db()

# Retrieve API keys from the database
TWILIO_ACCOUNT_SID = get_key("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = get_key("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = get_key("TWILIO_PHONE_NUMBER")
OPENAI_API_KEY = get_key("OPENAI_API_KEY")
ELEVEN_LABS_API_KEY = get_key("ELEVEN_LABS_API_KEY")

def synthesize_speech(text, filename="answer"):
    """ Converts text to speech using an external API and saves it as an MP3 file.
    :param text: Text to be converted to speech.
    :param filename: Name of the file to save the audio to.
    :return: Path to the saved audio file.
    """
    try:
        CHUNK_SIZE = 1024
        url = "https://api.elevenlabs.io/v1/text-to-speech/2zRM7PkgwBPiau2jvVXc"
        api_key = ELEVEN_LABS_API_KEY
        print("API and endpoint configurations set.")
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        print("HTTP headers configured.")
        data = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        print("Request payload prepared.")
        response = requests.post(url, json=data, headers=headers)
        print("POST request made to text-to-speech API.")
        if response.status_code == 200:
            safe_filename = secure_filename(filename)
            print(f"Filename secured: {safe_filename}")
            file_path = os.path.join(current_app.root_path, 'static', f"{safe_filename}.mp3")
            print(f"File path constructed: {file_path}")
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    f.write(chunk)
            print(f"File written to disk at: {file_path}")
            return file_path
        else:
            print(f"Failed to generate speech, server responded with status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error in generating speech: {e}")
        return None

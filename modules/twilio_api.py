from twilio.twiml.voice_response import VoiceResponse, Gather
from .mongodb import has_interacted_before
from twilio.rest import Client
from config import NGROK_URL
from flask import Flask, request, url_for
import os
import sqlite3

# Function to get the database path
def get_db_path():
    return os.path.join(os.path.dirname(__file__), '..\data\config.db')

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

# Debugging information to ensure keys are being retrieved
print(f"TWILIO_ACCOUNT_SID: {TWILIO_ACCOUNT_SID}")
print(f"TWILIO_AUTH_TOKEN: {TWILIO_AUTH_TOKEN}")
print(f"TWILIO_PHONE_NUMBER: {TWILIO_PHONE_NUMBER}")
print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")
print(f"ELEVEN_LABS_API_KEY: {ELEVEN_LABS_API_KEY}")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def handle_incoming_call(request_body):
    print("Handling incoming call from: ", request_body['From'])
    response = VoiceResponse()
    # First, play the pre-recorded response
    response.play(url_for('static', filename=f'response.mp3', _external=True))
    gather = Gather(input='speech', action=f'https://{NGROK_URL}/handle_speech1', timeout=10, speechTimeout='auto')
    response.append(gather)
    return str(response)

def initiate_call(phone_number, user_prompt):
    print("Initiating call to: ", phone_number)
    to_number = phone_number

    # Ensure the TWILIO_PHONE_NUMBER is correctly used
    if not TWILIO_PHONE_NUMBER:
        print("TWILIO_PHONE_NUMBER is not set")
        return "Failed to initiate call. TWILIO_PHONE_NUMBER is not set."

    # Initiate the call with correct TwiML
    call = twilio_client.calls.create(
        twiml=f'<Response><Say>{user_prompt}</Say><Gather action="https://{NGROK_URL}/handle_speech" input="speech" timeout="10" speechTimeout="auto"></Gather></Response>',
        to=to_number,
        from_=TWILIO_PHONE_NUMBER
    )

    return "Call initiated."


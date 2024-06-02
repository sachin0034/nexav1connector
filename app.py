from flask import Flask, request, url_for, jsonify
from modules.twilio_api import handle_incoming_call, initiate_call
from twilio.twiml.voice_response import VoiceResponse, Gather
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, NGROK_URL
from twilio.rest import Client
from modules.chatbot import get_chatbot_response
from modules.tts import synthesize_speech
import os
import sqlite3
from datetime import datetime
from flask_cors import CORS

# Function to get the database path
def get_db_path():
    return os.path.join(os.path.dirname(__file__), 'data/config.db')

def get_transcript_data():
    return os.path.join(os.path.dirname(__file__), 'data/transcripts.db')


def init_db_trans():
    db_transcript_data = get_transcript_data()
    os.makedirs(os.path.dirname(db_transcript_data), exist_ok=True)  # Ensure the directory exists
    conn = sqlite3.connect(db_transcript_data)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS transcripts
                      (call_sid TEXT PRIMARY KEY, conversation TEXT)''')
    conn.commit()
    conn.close()

def init_db():
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)  # Ensure the directory exists
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS config
                      (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit()
    conn.close()

def get_key(key):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_transcript(call_sid, conversation):
    conn = sqlite3.connect(get_transcript_data())
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO transcripts (call_sid, conversation) VALUES (?, ?)',
                   (call_sid, conversation))
    conn.commit()
    conn.close()

def get_transcript(call_sid):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('SELECT conversation FROM transcripts WHERE call_sid = ?', (call_sid,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Initialize the database and create the table if it doesn't exist
init_db()
init_db_trans()

TWILIO_ACCOUNT_SID = get_key("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = get_key("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = get_key("TWILIO_PHONE_NUMBER")
OPENAI_API_KEY = get_key("OPENAI_API_KEY")
ELEVEN_LABS_API_KEY = get_key("ELEVEN_LABS_API_KEY")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
static_dir = os.path.join(os.getcwd(), 'static')

app = Flask(__name__)
ngrok_url = NGROK_URL
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Authorization", "Content-Type"]}})

def secure_filename(filename):
    """Sanitize the filename to prevent directory traversal or other security risks."""
    filename = filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
    return f"{filename}.mp3"

@app.route('/', methods=['GET'])
def index():
    print("Handling request for index route")
    response_data = {
        "message": "Welcome to the AI calling agent Bot API Ver-1.2.2",
        "status": "success",
    }
    return jsonify(response_data)

@app.route('/voice', methods=['POST'])
def voice():
    print("Handling request for voice route")
    response = handle_incoming_call(request.values)
    return response

@app.route('/response_audio', methods=['POST', 'GET'])
def response_audio():
    print("Handling request for response_audio route")
    response = VoiceResponse()
    response.play(url_for('static', filename='response.mp3', _external=True))
    return str(response)


# Function to handle incoming calls
def handle_incoming_call(request_body):
    response = VoiceResponse()
    gather = Gather(input='speech', action='/handle_speech', timeout=10, speechTimeout='auto')
    response.append(gather)
    return str(response)

@app.route('/make_call', methods=['GET'])
def make_call():
    print("Handling request for make_call route")
    phone_number = request.args.get('phone_number')
    user_prompt = request.args.get('prompt')
    if phone_number and user_prompt:
        call_status = initiate_call(phone_number, user_prompt)
        return jsonify({"message": "Call initiated to " + phone_number, "status": call_status})
    else:
        return jsonify({"error": "Phone number and prompt are required"}), 400


@app.route('/handle_speech', methods=['POST', 'GET'])
def handle_speech():
    print("Handling request for handle_speech route")
    request_body = request.values
    response = VoiceResponse()
    if 'SpeechResult' in request_body:
        user_speech = request_body['SpeechResult']
        user_phone = request_body.get('To')
        call_sid = request_body.get('CallSid')
        user_prompt = request.args.get('prompt', '')  # Get the user's prompt
        chat_response = get_chatbot_response(user_speech, user_phone, user_prompt)  # Pass the user's prompt to the chatbot
        secure_audio_filename = secure_filename(f"response_{datetime.now().timestamp()}")
        audio_path = synthesize_speech(chat_response, secure_audio_filename)
        audio_url = url_for('static', filename=os.path.basename(audio_path), _external=True)
        response.play(audio_url)
        print(f"Audio played: {audio_url}")
        gather = Gather(input='speech', action=f'http://{NGROK_URL}/handle_speech', timeout=10, speechTimeout='auto')
        response.append(gather)

        # Save transcript to SQLite
        transcript_entry = {
            "call_sid": call_sid,
            "conversation": [
                {"speaker": "User", "text": user_speech},
                {"speaker": "AI", "text": chat_response}
            ]
        }
        save_transcript(call_sid, str(transcript_entry))

        if 'goodbye' in user_speech.lower():
            response.say("Thank you for using us. Goodbye!")
            response.hangup()
    return str(response)


@app.route('/handle_speech1', methods=['POST', 'GET'])
def handle_speech1():
    print("Handling request for handle_speech1 route")
    request_body = request.values
    response = VoiceResponse()
    if 'SpeechResult' in request_body:
        user_speech = request_body['SpeechResult']
        user_phone = request_body.get('From')
        call_sid = request_body.get('CallSid')
        chat_response = get_chatbot_response(user_speech, user_phone)
        secure_audio_filename = secure_filename(f"response_{datetime.now().timestamp()}")
        audio_path = synthesize_speech(chat_response, secure_audio_filename)
        audio_url = url_for('static', filename=os.path.basename(audio_path), _external=True)
        response.play(audio_url)
        print(f"Audio played: {audio_url}")
        gather = Gather(input='speech', action=f'http://{NGROK_URL}/handle_speech1', timeout=10, speechTimeout='auto')
        response.append(gather)

        # Save transcript to SQLite
        transcript_entry = {
            "call_sid": call_sid,
            "conversation": [
                {"speaker": "User", "text": user_speech},
                {"speaker": "AI", "text": chat_response}
            ]
        }
        save_transcript(call_sid, str(transcript_entry))

        if 'goodbye' in user_speech.lower():
            response.say("Thank you for using us. Goodbye!")
            response.hangup()
    return str(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, threaded=True)

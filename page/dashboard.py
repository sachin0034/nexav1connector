import streamlit as st
from time import sleep
from st_pages import hide_pages
import sqlite3
import os
import requests
from twilio.rest import Client
import pandas as pd
import plotly.express as px
from pymongo import MongoClient

# Function to get the database path
def get_db_path():
    return os.path.join(os.path.dirname(__file__), '../data/config.db')

def get_transcript_data():
    return os.path.join(os.path.dirname(__file__), '../data/transcripts.db')

def init_db_trans():
    db_transcript_data = get_transcript_data()
    os.makedirs(os.path.dirname(db_transcript_data), exist_ok=True)  # Ensure the directory exists
    conn = sqlite3.connect(db_transcript_data)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS transcripts
                      (call_sid TEXT PRIMARY KEY, conversation TEXT)''')
    conn.commit()
    conn.close()
    print("Database and table initialized for transcripts")

# Function to handle logout
def handle_logout():
    st.session_state.user_authenticated = False
    st.success("Logged out!")
    sleep(0.5)
    st.experimental_rerun()

# Hide the login page from the sidebar when logged in
hide_pages(["login"])

# Initialize the database
def init_db():
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)  # Ensure the directory exists
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS config
                      (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit()
    conn.close()
    print("Database and table initialized for config")

def get_key(key):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_key(key, value):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()
    print(f"Key '{key}' set with value '{value}'")

def check_missing_keys(keys):
    missing_keys = [key for key in keys if not get_key(key)]
    return missing_keys

def get_transcript(call_sid):
    conn = sqlite3.connect(get_transcript_data())
    cursor = conn.cursor()
    print(f"Fetching transcript for Call SID: {call_sid}")
    cursor.execute('SELECT conversation FROM transcripts WHERE call_sid = ?', (call_sid,))
    result = cursor.fetchone()
    conn.close()
    if result:
        transcript = result[0]
        print(f"Transcript found for Call SID: {call_sid}, Result: {transcript}")
        try:
            transcript_data = eval(transcript)
            return transcript_data
        except (TypeError, SyntaxError):
            print(f"Error: Invalid transcript data format for Call SID: {call_sid}")
            return None
    else:
        print(f"No transcript found for Call SID: {call_sid}")
        return None

init_db()
init_db_trans()

# Sidebar options with styling
st.sidebar.markdown(
    """
    <style>
        .stRadio > div {
            display: flex;
            flex-direction: column;
        }
        .stRadio > div > label {
            margin: 3px 0;
            padding: 10px;
            border-radius: 10px;
            border: 1px solid #ddd;
            cursor: pointer;
            display: flex;
            align-items: center;
            width : 250px;
        }
        .stRadio > div > label:hover {
            background-color: #FF69B4;
        }
        .stRadio > div > label > div:first-child {
            display: none;
        }
        .stRadio > div > label > div:first-child + div {
            display: block;
            margin-left: 10px;
        }
    </style>
    <div class="sidebar-box">
        <div class="sidebar-radio">
    """, unsafe_allow_html=True
)

# Add logo at the top of the sidebar
st.sidebar.image('logo.png', use_column_width=True)

option = st.sidebar.radio("", ("Dashboard", "Single Call", "Bulk Call", "Call Logs", "Transcripts", "Configuration", "Credits", "Logout"))

# Required keys
required_keys = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]

# Dashboard content
if option == "Dashboard":
    st.title("Dashboard")
    st.write("Welcome to the Dashboard!")

    # Sample data for the line chart
    data = {
        "days": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5"],
        "Parameter A": [10, 20, 15, 25, 20],
        "Parameter B": [30, 25, 35, 20, 30],
        "Parameter C": [20, 15, 25, 10, 20],
        "Parameter D": [25, 30, 20, 35, 25],
        "Parameter E": [15, 10, 20, 30, 15]
    }

    # Convert data to DataFrame
    df = pd.DataFrame(data)

    # Create the line chart
    fig = px.line(df, x="days", y=["Parameter A", "Parameter B", "Parameter C", "Parameter D", "Parameter E"], 
                  labels={"value": "Values", "variable": "Parameters"}, 
                  title="Sample Line Chart with Multiple Parameters")

    # Display the line chart
    st.plotly_chart(fig, use_container_width=True)

# Single Call content
elif option == "Single Call":
    missing_keys = check_missing_keys(required_keys)
    if missing_keys:
        st.error(f"The following keys are missing: {', '.join(missing_keys)}. Please update the configuration.")
    else:
        st.title("Single Call")
        phone_number = st.text_input("Enter Phone Number (with country code):")
        user_prompt = st.text_area("Enter the Prompt:")
        if st.button("Make Call"):
            if phone_number and user_prompt:
                response = requests.get(f"http://127.0.0.1:5000/make_call?phone_number={phone_number}&prompt={user_prompt}")
                if response.status_code == 200:
                    st.success("Call initiated successfully!")
                else:
                    st.error("Failed to initiate call. Please try again.")
            else:
                st.error("Please provide both phone number and prompt.")

# Bulk Call content
elif option == "Bulk Call":
    missing_keys = check_missing_keys(required_keys)
    if missing_keys:
        st.error(f"The following keys are missing: {', '.join(missing_keys)}. Please update the configuration.")
    else:
        st.title("Bulk Call")
        st.write("Make bulk calls.")
        
        uploaded_file = st.file_uploader("Upload file with phone numbers (CSV)", type=["csv"])
        user_prompt = st.text_area("Enter the Prompt:")
        
        if st.button("Make Call"):
            if uploaded_file and user_prompt:
                df = pd.read_csv(uploaded_file)
                if 'phone_number' in df.columns:
                    for index, row in df.iterrows():
                        phone_number = row['phone_number']
                        response = requests.get(f"http://127.0.0.1:5000/make_call?phone_number={phone_number}&prompt={user_prompt}")
                        if response.status_code == 200:
                            st.write(f"Call to {phone_number} initiated successfully!")
                        else:
                            st.write(f"Failed to initiate call to {phone_number}.")
                    st.success("Bulk call process completed!")
                else:
                    st.error("CSV file must contain 'phone_number' column.")
            else:
                st.error("Please upload a file and provide a prompt.")


# Call Logs content
elif option == "Call Logs":
    st.title("Call Logs")
    st.write("View call logs.")
    
    twilio_sid = get_key("TWILIO_ACCOUNT_SID")
    twilio_token = get_key("TWILIO_AUTH_TOKEN")
    
    if not twilio_sid or not twilio_token:
        st.error("Twilio SID and Auth Token are required in the configuration.")
    else:
        client = Client(twilio_sid, twilio_token)
        calls = client.calls.list(limit=20)
        
        if not calls:
            st.write("No call logs available.")
        else:
            data = []
            for call in calls:
                data.append({
                    "SID": call.sid,
                    "From": call.from_formatted,
                    "To": call.to_formatted,
                    "Status": call.status,
                    "Start Time": call.start_time,
                    "Duration": call.duration,
                })
            
            st.write(pd.DataFrame(data))

# Transcripts content
elif option == "Transcripts":
    st.title("Transcripts")
    call_sid = st.text_input("Enter Call SID:")

    if st.button("Fetch Transcript"):
        if call_sid:
            transcript_data = get_transcript(call_sid)
            if transcript_data:
                st.write("Transcript:")
                for entry in transcript_data['conversation']:
                    st.write(f"{entry['speaker']}: {entry['text']}")
            else:
                st.error("No transcript found for the entered Call SID.")
        else:
            st.error("Please enter a Call SID.")

elif option == "Configuration":
    st.title("Configuration")
    st.write("Configure your API keys.")

    with st.form(key='config_form'):
        twilio_sid = st.text_input("Twilio SID", get_key("TWILIO_ACCOUNT_SID") or "")
        twilio_token = st.text_input("Twilio Auth Token", get_key("TWILIO_AUTH_TOKEN") or "")
        twilio_phone = st.text_input("Twilio Phone Number", get_key("TWILIO_PHONE_NUMBER") or "")
        openai_key = st.text_input("OpenAI API Key", get_key("OPENAI_API_KEY") or "")
        elevenlabs_key = st.text_input("Eleven Labs API Key", get_key("ELEVEN_LABS_API_KEY") or "")

        submit_button = st.form_submit_button(label='Save')

        if submit_button:
            set_key("TWILIO_ACCOUNT_SID", twilio_sid)
            set_key("TWILIO_AUTH_TOKEN", twilio_token)
            set_key("TWILIO_PHONE_NUMBER", twilio_phone)
            set_key("OPENAI_API_KEY", openai_key)
            set_key("ELEVEN_LABS_API_KEY", elevenlabs_key)
            
            missing_keys = check_missing_keys(required_keys)
            if missing_keys:
                st.warning(f"The following keys are still missing: {', '.join(missing_keys)}. Please update the configuration.")
            else:
                st.success("Configuration saved successfully!")

# Credits content
elif option == "Credits":
    st.title("Credits")
    st.write("Add credits to your account.")

    with st.form(key='credits_form'):
        credits = st.number_input("Enter the amount of credits:", min_value=0)
        submit_button = st.form_submit_button(label='Add Credits')

        if submit_button:
            current_credits = int(get_key("CREDITS") or 0)
            new_credits = current_credits + credits
            set_key("CREDITS", str(new_credits))
            st.success(f"Credits added successfully! New balance: {new_credits} credits.")

# Logout content
elif option == "Logout":
    handle_logout()
    st.write("You have been logged out.")

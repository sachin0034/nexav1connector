from openai import OpenAI
from config import OPENAI_API_KEY
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.agents import OpenAIFunctionsAgent, AgentExecutor
from langchain.agents.openai_functions_agent.agent_token_buffer_memory import (AgentTokenBufferMemory, )
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, AIMessage, HumanMessage
from langchain.prompts import MessagesPlaceholder
from langchain.agents import AgentExecutor
from langchain.tools import StructuredTool
from langchain_community.llms import OpenAI
from .agent_tools import (booking, get_history, set_history)
from config import OPENAI_API_KEY
from langchain.prompts.prompt import PromptTemplate
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from openai import OpenAI
import sqlite3
import os

# Function to get the database path
def get_db_path():
    return os.path.join(os.path.dirname(__file__), '..\\data\\config.db')

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

# Initialize OpenAI client with the retrieved API key
client = OpenAI(api_key=OPENAI_API_KEY)

def book_appointment(user_phone: str, user_message: str, appointment_time: str) -> str:
    """Book an appointment for the user"""
    if not user_phone:
        return "Please provide your phone number"
    if not user_message:
        return "Please provide your location"
    booking(user_phone, user_message, appointment_time)
    return "Your appointment has been booked"

def get_chatbot_response_agent(query, user_phone, history=None):
    if history is None:
        history = {"messages": []}

    msg = []

    # Process history messages
    try:
        history_records = get_history(user_phone)
        if history_records and "messages" in history_records:
            for message_data in history_records["messages"]:
                role = message_data['role']
                content = message_data['content']
                if role == 'assistant':
                    msg.append(AIMessage(content=content))
                elif role == 'user':
                    msg.append(HumanMessage(content=content))
        else:
            starter_message = "Your AI therapist, feel free to share anything."
            msg.append(AIMessage(content=starter_message))
            history["messages"].append({'role': 'assistant', 'content': starter_message})
    except Exception as e:
        # Initialize history if get_history returns None
        history = {"messages": []}
        starter_message = "Your AI therapist, feel free to share anything."
        msg.append(AIMessage(content=starter_message))
        history["messages"].append({'role': 'assistant', 'content': starter_message})
        print(f"Error in getting chat history: {e}")

    msg.append(HumanMessage(content=query))
    history["messages"].append({'role': 'user', 'content': query})

    message = SystemMessage(content=(
        """
        Act as a friend and talk to user reply to their response what they in a politely way and provide
        the all the information to the user that they are looking for
        """
    ))

    prompt = OpenAIFunctionsAgent.create_prompt(
        system_message=message,
        extra_prompt_messages=[MessagesPlaceholder(variable_name="history")],
    )
    llm = ChatOpenAI(temperature=0.4, streaming=True, model="gpt-4-1106-preview", max_retries=2, max_tokens=150)

    agent = OpenAIFunctionsAgent(llm=llm, prompt=prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        verbose=False,
        return_intermediate_steps=False,
    )
    print(msg)
    # Append the AI response to the history
    response = agent_executor(
        {
            "input": query,
            "history": msg,
        },
        include_run_info=True,
    )
    history["messages"].append({'role': 'assistant', 'content': response["output"]})

    # Update the user's history in the database
    set_history(user_phone, history["messages"])

    return response['output']

def get_chatbot_response(query, user_phone, user_prompt, history=[]):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": user_prompt},  # Use the user's prompt
            {"role": "user", "content": query}
        ],
        max_tokens=70,
        temperature=0.5
    )

    return completion.choices[0].message.content


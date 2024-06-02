import streamlit as st
import sqlite3
import re
import os

# Function to get the database path
def get_db_path():
    return os.path.join(os.path.dirname(__file__), '../data/users.db')

# Function to create the Users database if it doesn't exist
def create_users_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

# Function to add a new user to the database
def add_user_to_db(email, password):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    insert_query = """
        INSERT INTO Users (email, password)
        VALUES (?, ?)
    """
    cursor.execute(insert_query, (email, password))
    conn.commit()
    conn.close()

# Function to authenticate a user
def authenticate_user(email, password):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    select_query = """
        SELECT * FROM Users WHERE email = ? AND password = ?
    """
    cursor.execute(select_query, (email, password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return True
    else:
        return False

# Function to initialize session states
def init_ses_states():
    st.session_state.setdefault('user_authenticated', False)

# Function to validate password
def approve_password(password):
    if len(password) < 8:
        return "Password must have at least 8 characters"
    elif not any(char.isdigit() for char in password):
        return "Password must contain at least one digit"
    elif not any(char in '_@$#!?&*%' for char in password):
        return "Password must contain at least one special character (_@$#!?&*%)"
    return True

# Function to validate email
def approve_email(email):
    email_regex = '^[a-zA-Z0-9]+[\._]?[a-zA-Z0-9]+[@]\w+[.]\w{2,3}$'
    if not re.match(email_regex, email):
        return "Invalid email format"
    return True

# Function to handle user authentication tab
def user_authentication_tab():
    st.title("User Authentication")
    login_tab, create_account_tab = st.tabs(["Login", "Create Account"])

    with login_tab:
        email = st.text_input("Email:")
        password = st.text_input("Password:", type='password')
        if st.button("Login"):
            if authenticate_user(email=email, password=password):
                st.session_state.user_authenticated = True
                st.experimental_rerun()  # Reload the page to switch to the dashboard
            else:
                st.error('Incorrect Username or Password.')

    with create_account_tab:
        new_email = st.text_input("New Email:")
        new_password = st.text_input("New Password:", type='password')
        confirm_password = st.text_input("Confirm Password:", type='password')
        if st.button("Create Account"):
            email_validation = approve_email(new_email)
            password_validation = approve_password(new_password)

            if email_validation is not True:
                st.error(email_validation)
                return
            if password_validation is not True:
                st.error(password_validation)
                return
            if new_password != confirm_password:
                st.error("Passwords do not match")
                return
            add_user_to_db(email=new_email, password=new_password)
            st.success(f"{new_email} Successfully Added")

# Main function to set up the app
def main():
    st.set_page_config(page_title="Nexa V1", page_icon=":call:")
    create_users_db()
    init_ses_states()
    st.title("Nexa V1")
    
    if not st.session_state.user_authenticated:
        user_authentication_tab()
    else:
        st.switch_page(page="dashboard")

# Run the main function
if __name__ == '__main__':
    main()

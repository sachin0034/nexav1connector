import sqlite3

def init_db():
    conn = sqlite3.connect('data/config.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS config
                      (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit()
    conn.close()

def get_key(key):
    conn = sqlite3.connect('config.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_key(key, value):
    conn = sqlite3.connect('config.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

# Initialize the database
init_db()

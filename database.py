import sqlite3
from pathlib import Path
from config import DATA_DIR

DB_PATH = DATA_DIR / "chatbot.db"

def get_db_connection():
    """Establish a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enables column access by name (e.g. row['username'])
    return conn

def init_db():
    """Create database tables if they do not already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create Users Table (Tracks distinct users & password credentials)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            groq_api_key TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. Create Sessions Table (Tracks distinct chat sessions for each user)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)
    
    # 3. Create Messages Table (Tracks chat history/memory for each session)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            sender TEXT CHECK(sender IN ('user', 'bot')),
            text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"[OK] SQLite Database initialized at: {DB_PATH}")

def hash_password(password: str) -> str:
    """Hash a password securely using PBKDF2 with a random salt."""
    import hashlib
    import secrets
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}:{key.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against its stored PBKDF2 hash."""
    import hashlib
    import secrets
    try:
        salt, key_hex = stored_hash.split(":", 1)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return secrets.compare_digest(key.hex(), key_hex)
    except Exception:
        return False

def create_user(email: str, password: str, groq_api_key: str = None) -> str:
    """Create a new user with a hashed password, returning their user_id."""
    import uuid
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, email, password_hash, groq_api_key) VALUES (?, ?, ?, ?)",
        (user_id, email.strip().lower(), password_hash, groq_api_key.strip() if groq_api_key else None)
    )
    conn.commit()
    conn.close()
    return user_id

def authenticate_user(email: str, password: str) -> str:
    """Authenticate a user by email/password, returning their user_id if successful, else None."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    conn.close()
    
    if user and verify_password(password, user['password_hash']):
        return user['user_id']
    return None

def get_user(user_id: str) -> dict:
    """Fetch user details by user_id."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def create_session(user_id: str, title: str = "New Chat") -> str:
    """Create a new chat session for a user and return the session_id (UUID)."""
    import uuid
    session_id = str(uuid.uuid4())
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (session_id, user_id, title) VALUES (?, ?, ?)",
        (session_id, user_id, title.strip())
    )
    conn.commit()
    conn.close()
    return session_id

def get_user_sessions(user_id: str) -> list:
    """Fetch all chat sessions associated with a user, sorted by creation date descending."""
    conn = get_db_connection()
    sessions = conn.execute(
        "SELECT * FROM sessions WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(s) for s in sessions]

def save_message(session_id: str, sender: str, text: str):
    """Save a chat message to history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (session_id, sender, text) VALUES (?, ?, ?)",
        (session_id, sender, text.strip())
    )
    conn.commit()
    conn.close()

def get_session_messages(session_id: str) -> list:
    """Fetch all messages inside a chat session, sorted chronologically."""
    conn = get_db_connection()
    messages = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(m) for m in messages]

def update_session_summary(session_id: str, summary: str):
    """Update the running conversation summary for a chat session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE sessions SET summary = ? WHERE session_id = ?",
        (summary.strip() if summary else None, session_id)
    )
    conn.commit()
    conn.close()

def get_session_summary(session_id: str) -> str:
    """Fetch the running conversation summary for a chat session."""
    conn = get_db_connection()
    row = conn.execute("SELECT summary FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
    conn.close()
    return row['summary'] if row and row['summary'] else ""

def update_user_api_key(user_id: str, api_key: str):
    """Update or save the user's custom Groq API Key."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET groq_api_key = ? WHERE user_id = ?",
        (api_key.strip() if api_key else None, user_id)
    )
    conn.commit()
    conn.close()

def delete_user(user_id: str):
    """Delete a user account and cascade delete all their sessions and messages."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Explicitly enable foreign key cascades in SQLite connection
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def delete_session(session_id: str):
    """Delete a specific chat session and all of its associated messages."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()

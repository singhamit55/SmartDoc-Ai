import os
import sqlite3
import datetime

DB_FILE = "./data/smartdoc.sqlite"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables for Phase 2 (Users, Conversations, Messages, Documents)
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'processed'
        );
    ''')
    conn.commit()
    conn.close()

# Initialize DB on load
init_db()

def get_chat_history(chat_id: str, limit: int = 4) -> str:
    """Returns a formatted string of the conversation history for a given chat_id."""
    if not chat_id:
        return ""
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch the last 'limit' messages to keep the prompt small
    cursor.execute('''
        SELECT role, content FROM messages 
        WHERE conversation_id = ? 
        ORDER BY created_at ASC
    ''', (chat_id,))
    
    messages = cursor.fetchall()
    conn.close()
    
    # Keep only the most recent interactions
    recent_messages = messages[-limit:] if len(messages) > limit else messages
    
    formatted = []
    for msg in recent_messages:
        role = "User" if msg["role"] == "user" else "AI"
        formatted.append(f"{role}: {msg['content']}")
        
    return "\n".join(formatted)

def add_message(chat_id: str, user_msg: str, ai_msg: str, user_id: str = None):
    """Appends a new interaction to the SQLite database, linked to the user."""
    if not chat_id:
        return
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure conversation exists and is linked to this user
    cursor.execute("SELECT id FROM conversations WHERE id = ?", (chat_id,))
    if not cursor.fetchone():
        title = user_msg[:30] + "..." if len(user_msg) > 30 else user_msg
        cursor.execute(
            "INSERT INTO conversations (id, user_id, title) VALUES (?, ?, ?)",
            (chat_id, user_id, title)
        )
        
    # Insert user and AI messages
    cursor.execute("INSERT INTO messages (conversation_id, role, content) VALUES (?, 'user', ?)", (chat_id, user_msg))
    cursor.execute("INSERT INTO messages (conversation_id, role, content) VALUES (?, 'ai', ?)", (chat_id, ai_msg))
    
    conn.commit()
    conn.close()

def get_all_chats(user_id: str = None):
    """Returns only this user's chat sessions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute('''
            SELECT id, title FROM conversations 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
    else:
        # Fallback: return nothing if no user_id provided (safety)
        conn.close()
        return []
    
    chats = cursor.fetchall()
    conn.close()
    
    return [{"id": chat["id"], "title": chat["title"]} for chat in chats]

def get_chat_messages(chat_id: str, user_id: str = None):
    """Returns messages for a chat, only if it belongs to this user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Security check: verify this chat belongs to the requesting user
    if user_id:
        cursor.execute("SELECT id FROM conversations WHERE id = ? AND user_id = ?", (chat_id, user_id))
        if not cursor.fetchone():
            conn.close()
            return []  # Return empty if chat doesn't belong to this user
    
    cursor.execute('''
        SELECT role, content FROM messages 
        WHERE conversation_id = ? 
        ORDER BY created_at ASC
    ''', (chat_id,))
    
    raw_messages = cursor.fetchall()
    conn.close()
    
    # Format into legacy structure for API compatibility: [{"user": "...", "ai": "..."}]
    result = []
    current_pair = {}
    for msg in raw_messages:
        if msg["role"] == "user":
            current_pair = {"user": msg["content"], "ai": ""}
        else:
            current_pair["ai"] = msg["content"]
            result.append(current_pair)
            current_pair = {}
            
    return result

def add_document(doc_id: str, filename: str):
    """Records an uploaded document in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO documents (id, filename, status) VALUES (?, ?, 'processed')", (doc_id, filename))
    conn.commit()
    conn.close()

def remove_document(filename: str):
    """Removes a document record from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM documents WHERE filename = ?", (filename,))
    conn.commit()
    conn.close()


import sqlite3
import json
import pandas as pd
from datetime import datetime

DATABASE_PATH = "application.db"


def init_database():
    """Create necessary tables if they don't exist."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_input TEXT,
                assistant_message TEXT,
                source_pages TEXT,
                time_user_input_sent TEXT,
                time_assistant_answered TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS layout_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                label TEXT,
                page TEXT,
                poly TEXT
            )
        ''')
        conn.commit()


def store_message(user_input, assistant_response, source_pages):
    now = datetime.now().strftime('%d/%m/%Y - %H:%M')
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (user_input, assistant_message, source_pages, time_user_input_sent, time_assistant_answered) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_input, assistant_response, json.dumps(source_pages), now, now))
        conn.commit()


def select_messages():
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_input, assistant_message, source_pages, time_user_input_sent, time_assistant_answered 
            FROM messages ORDER BY time_user_input_sent ASC
        ''')
        messages = cursor.fetchall()
    return messages


def select_layout_analysis(page_label: str) -> pd.DataFrame:
    """Return layout analysis results for a given page label (e.g., 'page_1')."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM layout_analysis WHERE page = ?', (page_label,))
        rows = cursor.fetchall()
    return pd.DataFrame(rows, columns=["id", "text", "label", "page", "poly"])


def insert_layout_analysis(data):
    """Insert a list of layout analysis entries (dicts with text, label, page, poly)."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        for item in data:
            if "text" in item and "label" in item and "page" in item and "poly" in item:
                cursor.execute('''
                    INSERT INTO layout_analysis (text, label, page, poly)
                    VALUES (?, ?, ?, ?)
                ''', (item['text'], item['label'], item['page'], json.dumps(item['poly'])))
        conn.commit()


def reset_layout_analysis_table():
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS layout_analysis")
        conn.commit()
    init_database()

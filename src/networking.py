"""Coffee chat / networking tracker — log conversations, takeaways, and action items."""

from datetime import datetime
from .scraper import get_db


def _ensure_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coffee_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_date TEXT,
            person_name TEXT,
            person_role TEXT,
            person_company TEXT,
            linkedin_url TEXT,
            how_connected TEXT,
            summary TEXT,
            key_takeaways TEXT,
            action_items TEXT,
            follow_up_date TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    return conn


def log_chat(person_name, person_role="", person_company="", chat_date=None,
             linkedin_url="", how_connected="", summary="", key_takeaways="",
             action_items="", follow_up_date=""):
    """Log a coffee chat. Takeaways/action_items can be newline-separated strings."""
    conn = _ensure_table()
    if not chat_date:
        chat_date = datetime.now().strftime("%Y-%m-%d")
    conn.execute("""
        INSERT INTO coffee_chats
        (chat_date, person_name, person_role, person_company, linkedin_url,
         how_connected, summary, key_takeaways, action_items, follow_up_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (chat_date, person_name, person_role, person_company, linkedin_url,
          how_connected, summary, key_takeaways, action_items, follow_up_date,
          datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_all_chats():
    conn = _ensure_table()
    cursor = conn.execute("SELECT * FROM coffee_chats ORDER BY chat_date DESC")
    columns = [d[0] for d in cursor.description]
    rows = [dict(zip(columns, r)) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_all_action_items():
    """Aggregate all action items across chats."""
    chats = get_all_chats()
    items = []
    for chat in chats:
        if chat.get("action_items"):
            for line in chat["action_items"].split("\n"):
                line = line.strip().lstrip("-•* ")
                if line:
                    items.append({"item": line, "from": chat["person_name"], "date": chat["chat_date"]})
    return items

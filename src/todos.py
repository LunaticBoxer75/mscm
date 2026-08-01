"""To-Do tracker — manual items + auto-imported coffee chat action items."""

from datetime import datetime
from .scraper import get_db


def _ensure_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            source TEXT DEFAULT 'manual',
            status TEXT DEFAULT 'open',
            priority TEXT DEFAULT 'medium',
            created_at TEXT,
            done_at TEXT
        )
    """)
    conn.commit()
    return conn


def add_todo(item, category="general", source="manual", priority="medium"):
    conn = _ensure_table()
    # Avoid duplicates by exact item text
    existing = conn.execute("SELECT id FROM todos WHERE item = ?", (item,)).fetchone()
    if existing:
        conn.close()
        return
    conn.execute("""
        INSERT INTO todos (item, category, source, priority, status, created_at)
        VALUES (?, ?, ?, ?, 'open', ?)
    """, (item, category, source, priority, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def set_status(todo_id, status):
    conn = _ensure_table()
    done_at = datetime.now().isoformat() if status == "done" else None
    conn.execute("UPDATE todos SET status = ?, done_at = ? WHERE id = ?", (status, done_at, todo_id))
    conn.commit()
    conn.close()


def get_todos(status=None):
    conn = _ensure_table()
    if status:
        cursor = conn.execute("SELECT * FROM todos WHERE status = ? ORDER BY created_at DESC", (status,))
    else:
        cursor = conn.execute("SELECT * FROM todos ORDER BY status, created_at DESC")
    columns = [d[0] for d in cursor.description]
    rows = [dict(zip(columns, r)) for r in cursor.fetchall()]
    conn.close()
    return rows


def import_coffee_chat_actions():
    """Pull action items from coffee chats into todos (dedup by text)."""
    from .networking import get_all_action_items
    items = get_all_action_items()
    for ai in items:
        add_todo(ai["item"], category="from-coffee-chat", source=ai["from"])
    return len(items)


def seed_defaults():
    """Seed important standing to-dos if not present."""
    defaults = [
        ("Brainstorm how to translate unique background (Microbiology + Uber policy/risk + SCM + AI) into a marketable strength for interviews & applications", "positioning", "Shivam Suru", "high"),
        ("Build STAR stories categorized by behavioral theme (conflict, prioritization, leadership, failure, ambiguity)", "interview-prep", "Shivam Suru", "high"),
        ("Compile top 20-40 H1B sponsoring companies and tailor resume to each culture", "job-search", "Shivam Suru", "high"),
        ("Schedule 2 coffee chats/week + 1 senior/partner chat", "networking", "Shivam Suru", "medium"),
        ("Do 1 mock interview every 2 weeks", "interview-prep", "Shivam Suru", "medium"),
    ]
    for item, cat, src, pri in defaults:
        add_todo(item, category=cat, source=src, priority=pri)

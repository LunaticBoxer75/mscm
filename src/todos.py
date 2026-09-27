"""To-Do tracker — manual items + auto-imported coffee chat action items.

Backed by src/user_store.py (durable JSON), not SQLite — see that module for why.
"""

from datetime import datetime

from . import user_store


def _todo(item, category="general", source="manual", priority="medium"):
    return {"item": item, "category": category, "source": source,
            "priority": priority, "status": "open", "done_at": None}


def add_todo(item, category="general", source="manual", priority="medium"):
    # Dedup by exact item text, checked inside the write so it's race-free
    return user_store.add_unique("todos", _todo(item, category, source, priority),
                                 unique_on="item", message="Add to-do")


def set_status(todo_id, status):
    user_store.update("todos", todo_id, {
        "status": status,
        "done_at": datetime.now().isoformat() if status == "done" else None,
    })


def get_todos(status=None):
    rows = user_store.get("todos")
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return sorted(
        rows,
        key=lambda r: (r.get("status") or "", r.get("created_at") or ""),
        reverse=True,
    )


def delete_todo(todo_id):
    return user_store.delete("todos", todo_id)


def import_coffee_chat_actions():
    """Pull action items from coffee chats into todos (dedup by text)."""
    from .networking import get_all_action_items

    items = get_all_action_items()
    existing = {t.get("item") for t in user_store.get("todos")}
    new = [_todo(ai["item"], "from-coffee-chat", ai["from"])
           for ai in items if ai["item"] not in existing]
    # Runs on every render: one commit for all new items, zero if none are new
    if new:
        user_store.add_many("todos", new, "Import coffee-chat action items", unique_on="item")
    return len(new)


def seed_defaults():
    """Seed important standing to-dos if not present."""
    defaults = [
        ("Brainstorm how to translate unique background (Microbiology + Uber policy/risk + SCM + AI) into a marketable strength for interviews & applications", "positioning", "Shivam Suru", "high"),
        ("Build STAR stories categorized by behavioral theme (conflict, prioritization, leadership, failure, ambiguity)", "interview-prep", "Shivam Suru", "high"),
        ("Compile top 20-40 H1B sponsoring companies and tailor resume to each culture", "job-search", "Shivam Suru", "high"),
        ("Schedule 2 coffee chats/week + 1 senior/partner chat", "networking", "Shivam Suru", "medium"),
        ("Do 1 mock interview every 2 weeks", "interview-prep", "Shivam Suru", "medium"),
    ]
    existing = {t.get("item") for t in user_store.get("todos")}
    new = [_todo(i, c, s, p) for i, c, s, p in defaults if i not in existing]
    if new:
        user_store.add_many("todos", new, "Seed standing to-dos", unique_on="item")

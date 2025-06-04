import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '../../server-assets/persistent/calendars.db')

# python -c "import components.common.calendar_db as calendar_db; print('Calendar DB initialized.')"

# ───────────────────────────────────────────────────────────────────────────────
#  DEBUG LOGGER
# ───────────────────────────────────────────────────────────────────────────────

try:
    from components.common.config import DEBUG_MODE, REACTPY_DEBUG_MODE
    if REACTPY_DEBUG_MODE:
        import reactpy
        reactpy.config.REACTPY_DEBUG_MODE.current = True
        print("[calendar_db.py DEBUG] REACTPY_DEBUG_MODE imported from config.py, using value:", REACTPY_DEBUG_MODE)
    if DEBUG_MODE:
        print("[calendar_db.py DEBUG] DEBUG_MODE imported from config.py, using value:", DEBUG_MODE)
except ImportError:
    DEBUG_MODE = False
    print("Warning: DEBUG_MODE not imported from config.py, using default value False.")

def debug_log(*args):
    if DEBUG_MODE:
        print("[calendar_db.py DEBUG]", *args)

def get_db():
    debug_log("Opening SQLite connection to", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    debug_log("Initializing calendar DB")
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS calendars (
            user_id TEXT PRIMARY KEY,
            ics TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
    debug_log("Calendar DB initialized")

def save_calendar(user_id, ics):
    import os
    debug_log("calendar_db.py loaded from", os.path.abspath(__file__))
    debug_log(f"Saving calendar for user_id={user_id}")
    conn = get_db()
    c = conn.cursor()
    c.execute('REPLACE INTO calendars (user_id, ics, updated_at) VALUES (?, ?, ?)', (user_id, ics, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    debug_log(f"Calendar saved for user_id={user_id}")

def get_calendar(user_id):
    import os
    debug_log("calendar_db.py loaded from", os.path.abspath(__file__))
    debug_log(f"Fetching calendar for user_id={user_id}")
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT ics FROM calendars WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    debug_log(f"Fetched calendar for user_id={user_id}: {'found' if row else 'not found'}")
    if row:
        debug_log(f"ICS content for user_id={user_id} (first 200 chars):\n{row['ics'][:200]}")
    return row['ics'] if row else None

init_db()

if __name__ == '__main__':
    print('Calendar DB initialized.')

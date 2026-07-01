from pathlib import Path
import os

from app.db import DB_PATH, init_db

p = Path(DB_PATH)
if p.exists():
    p.unlink()
    print(f"Removed: {p}")
init_db()
print(f"Database initialized: {p}")

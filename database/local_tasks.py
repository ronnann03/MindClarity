"""Persistencia local de tareas cuando Supabase no está conectado."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import uuid
from contextlib import contextmanager

from config.settings import settings


class LocalTasks:
    def __init__(self, path: Path | None = None):
        self.path = path or settings.cache_dir / 'yu-tasks.sqlite3'

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT, status TEXT, due_at TEXT, created_at TEXT)')
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, data):
        row = {'id':uuid.uuid4().hex[:10], 'title':data['title'], 'description':data.get('description',''),
               'status':'pending', 'due_at':data.get('due_at'), 'created_at':datetime.now(timezone.utc).isoformat()}
        with self.connect() as db:
            db.execute('INSERT INTO tasks VALUES (:id,:title,:description,:status,:due_at,:created_at)',row)
        return row

    def pending(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM tasks WHERE status='pending' ORDER BY created_at DESC LIMIT 50")]

    def complete(self, task_id):
        with self.connect() as db:
            return db.execute("UPDATE tasks SET status='done' WHERE id=? AND status='pending'",(task_id,)).rowcount > 0


local_tasks = LocalTasks()

import sqlite3
import json
from threading import Thread
import time
import uuid
import asyncio

class TaskQueue:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS tasks
                     (id TEXT PRIMARY KEY, name TEXT, status TEXT, progress TEXT, result TEXT)''')
        conn.commit()
        conn.close()

    def add_task(self, task_func, task_name, *args, **kwargs):
        task_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO tasks VALUES (?, ?, ?, ?, ?)", (task_id, task_name, "pending", "0", None))
        conn.commit()
        conn.close()

        Thread(target=self._run_task, args=(task_id, task_func, args, kwargs)).start()
        return task_id

    def _run_task(self, task_id, task_func, args, kwargs):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(task_func(task_id, *args, **kwargs))
            self._update_task(task_id, "completed", "100", result)
        except Exception as e:
            self._update_task(task_id, "failed", "0", str(e))
        finally:
            loop.close()

    def _update_task(self, task_id, status, progress, result):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE tasks SET status = ?, progress = ?, result = ? WHERE id = ?",
                  (status, str(progress), json.dumps(result), task_id))
        conn.commit()
        conn.close()

    def get_task_status(self, task_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT name, status, progress, result FROM tasks WHERE id = ?", (task_id,))
        result = c.fetchone()
        conn.close()
        if result:
            return {
                "id": task_id,
                "name": result[0],
                "status": result[1],
                "progress": result[2],
                "result": json.loads(result[3]) if result[3] else None
            }
        return None

    def get_all_tasks(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, name, status, progress FROM tasks ORDER BY rowid DESC LIMIT 10")
        tasks = [
            {
                "id": row[0],
                "name": row[1],
                "status": row[2],
                "progress": row[3]
            } for row in c.fetchall()
        ]
        conn.close()
        return tasks

task_queue = TaskQueue("tasks.db")
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
                     (id TEXT PRIMARY KEY, status TEXT, result TEXT)''')
        conn.commit()
        conn.close()

    def add_task(self, task_func, *args, **kwargs):
        task_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO tasks VALUES (?, ?, ?)", (task_id, "pending", None))
        conn.commit()
        conn.close()

        Thread(target=self._run_task, args=(task_id, task_func, args, kwargs)).start()
        return task_id

    def _run_task(self, task_id, task_func, args, kwargs):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(task_func(*args, **kwargs))
            self._update_task(task_id, "completed", result)
        except Exception as e:
            self._update_task(task_id, "failed", str(e))
        finally:
            loop.close()

    def _update_task(self, task_id, status, result):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE tasks SET status = ?, result = ? WHERE id = ?",
                  (status, json.dumps(result), task_id))
        conn.commit()
        conn.close()

    def get_task_status(self, task_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT status, result FROM tasks WHERE id = ?", (task_id,))
        result = c.fetchone()
        conn.close()
        if result:
            return {"status": result[0], "result": json.loads(result[1]) if result[1] else None}
        return None

    def get_all_tasks(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, status FROM tasks")
        tasks = [{"id": row[0], "status": row[1]} for row in c.fetchall()]
        conn.close()
        return tasks

task_queue = TaskQueue("tasks.db")
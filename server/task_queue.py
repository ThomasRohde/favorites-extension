from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from threading import Thread
import asyncio
import uuid
import json

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    status = Column(String)
    progress = Column(String)
    result = Column(JSON)

class TaskQueue:
    def __init__(self):
        self.init_db()

    def init_db(self):
        Base.metadata.create_all(bind=engine)

    def add_task(self, task_func, task_name, *args, **kwargs):
        task_id = str(uuid.uuid4())
        with SessionLocal() as db:
            db_task = Task(id=task_id, name=task_name, status="pending", progress="0", result=None)
            db.add(db_task)
            db.commit()

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
        with SessionLocal() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = status
                task.progress = progress
                task.result = result
                db.commit()

    def get_task_status(self, task_id):
        with SessionLocal() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            return {
                "id": task.id,
                "name": task.name,
                "status": task.status,
                "progress": task.progress,
                "result": task.result
            }
        return None

    def get_all_tasks(self):
        with SessionLocal() as db:
            tasks = db.query(Task).order_by(Task.id.desc()).limit(10).all()
        return [
            {
                "id": task.id,
                "name": task.name,
                "status": task.status,
                "progress": task.progress
            } for task in tasks
        ]

task_queue = TaskQueue()
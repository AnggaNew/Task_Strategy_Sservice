"""Contoh penggunaan; panggil scheduler.run_pending() secara periodik dari worker."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from task_service.actions import BackupAction, DeleteAction, SyncAction
from task_service.executor import TaskExecutor
from task_service.models import Task
from task_service.scheduler import DailyScheduler
from task_service.users import UserManager


def build_scheduler() -> DailyScheduler:
    raw_tasks = [
        {"user": "alice", "time": "12:00", "action": "sync", "target": "/data/x"},
        {"user": "bob", "time": "12:00", "action": "backup", "target": "/srv/y"},
        {"user": "alice", "time": "12:00", "action": "delete", "target": "/tmp/z"},
    ]
    users = UserManager({"alice": 3, "bob": 5})
    actions = {"sync": SyncAction(), "backup": BackupAction(), "delete": DeleteAction()}
    return DailyScheduler([Task.from_dict(item) for item in raw_tasks], TaskExecutor(users, actions))


def build_mysql_scheduler():
    """Membuat scheduler produksi dari variabel lingkungan DATABASE_URL."""
    from task_service.mysql import (
        MySQLConnectionFactory,
        MySQLDailyScheduler,
        MySQLRunRepository,
        MySQLTaskExecutor,
        MySQLTaskRepository,
    )
    connections = MySQLConnectionFactory()
    actions = {"sync": SyncAction(), "backup": BackupAction(), "delete": DeleteAction()}
    return MySQLDailyScheduler(
        MySQLTaskRepository(connections),
        MySQLTaskExecutor(MySQLRunRepository(connections), actions),
    )


if __name__ == "__main__":
    load_dotenv(Path(__file__).resolve().parent / ".env.mysql", override=False)
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    scheduler = build_mysql_scheduler()
    scheduler.run_pending()

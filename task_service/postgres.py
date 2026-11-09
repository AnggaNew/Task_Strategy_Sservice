"""Adapter PostgreSQL untuk penyimpanan task dan riwayat eksekusi."""

import logging
import os
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from .models import Task, TaskResult


class PostgresConnectionFactory:
    """Membuat koneksi baru per operasi untuk worker sinkron sederhana."""

    def __init__(self, database_url=None):
        self._database_url = database_url or os.getenv("DATABASE_URL")
        if not self._database_url:
            raise ValueError("DATABASE_URL wajib diatur")

    def connect(self):
        return psycopg2.connect(self._database_url)


class PostgresTaskRepository:
    def __init__(self, connections):
        self._connections = connections

    def list_due(self, now):
        query = """
            SELECT id, user_id, scheduled_time, action, parameters, enabled
            FROM tasks
            WHERE enabled = TRUE AND scheduled_time <= %(current_time)s
            ORDER BY scheduled_time, id
        """
        with self._connections.connect() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, {"current_time": now.time()})
                rows = cursor.fetchall()
        return [Task(str(row["user_id"]), row["scheduled_time"], row["action"],
                     row["parameters"], str(row["id"]), row["enabled"]) for row in rows]


class PostgresRunRepository:
    def __init__(self, connections):
        self._connections = connections

    def claim(self, task_id, scheduled_date):
        with self._connections.connect() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM claim_task_run(%(task_id)s::uuid, %(scheduled_date)s)",
                               {"task_id": task_id, "scheduled_date": scheduled_date})
                return dict(cursor.fetchone())

    def mark_running(self, run_id):
        self._set_status(run_id, "running", started=True)

    def mark_finished(self, run_id, status, message):
        if status not in ("succeeded", "failed"):
            raise ValueError("Status akhir tidak valid")
        self._set_status(run_id, status, message, finished=True)

    def _set_status(self, run_id, status, message=None, started=False, finished=False):
        query = "UPDATE task_runs SET status = %(status)s, message = %(message)s"
        if started:
            query += ", started_at = now()"
        if finished:
            query += ", finished_at = now()"
        query += " WHERE id = %(run_id)s::uuid"
        with self._connections.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, {"run_id": run_id, "status": status, "message": message})
                if cursor.rowcount != 1:
                    raise KeyError("Task run tidak ditemukan: {0}".format(run_id))


class PostgresTaskExecutor:
    """Menjalankan action setelah run diklaim secara atomik oleh PostgreSQL."""

    def __init__(self, runs, actions):
        self._runs = runs
        self._actions = actions
        self._logger = logging.getLogger(__name__)

    def execute(self, task, on_date):
        action = self._actions.get(task.action)
        if action is None:
            message = "Aksi tidak terdaftar: {0}".format(task.action)
            self._logger.error("Task gagal task_id=%s: %s", task.id, message)
            return TaskResult(task.id, False, message)
        try:
            run = self._runs.claim(task.id, on_date)
        except Exception:
            self._logger.exception("Gagal mengklaim task_id=%s", task.id)
            return TaskResult(task.id, False, "Gagal mengklaim eksekusi task")
        if run["status"] == "rejected_quota":
            return TaskResult(task.id, False, run["message"])
        if run["status"] != "pending":
            return TaskResult(task.id, False, "Task telah diklaim sebelumnya: {0}".format(run["status"]))
        try:
            self._runs.mark_running(run["id"])
            message = action.execute(task.parameters)
            self._runs.mark_finished(run["id"], "succeeded", message)
            self._logger.info("Task berhasil task_id=%s run_id=%s", task.id, run["id"])
            return TaskResult(task.id, True, message)
        except Exception as error:
            self._logger.exception("Task gagal task_id=%s run_id=%s", task.id, run["id"])
            message = str(error) or "Kesalahan eksekusi tak terduga"
            try:
                self._runs.mark_finished(run["id"], "failed", message)
            except Exception:
                self._logger.exception("Gagal memperbarui run failed run_id=%s", run["id"])
            return TaskResult(task.id, False, message)


class PostgresDailyScheduler:
    def __init__(self, tasks, executor):
        self._tasks = tasks
        self._executor = executor

    def run_pending(self, now=None):
        now = now or datetime.now()
        return [self._executor.execute(task, now.date()) for task in self._tasks.list_due(now)]

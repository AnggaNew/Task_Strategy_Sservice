"""Repository MySQL: klaim dan reservasi kuota dalam satu transaksi InnoDB."""

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlsplit
from uuid import uuid4

import pymysql
from .models import Task, TaskResult


class MySQLConnectionFactory:
    def __init__(self, database_url=None):
        url = urlsplit(database_url or os.getenv('MYSQL_DATABASE_URL') or os.getenv('DATABASE_URL', ''))
        if url.scheme != 'mysql' or not url.hostname or not url.username or not url.path.strip('/'):
            raise ValueError('Isi MYSQL_DATABASE_URL dengan mysql://USER:PASSWORD@HOST:3306/task_strattegy')
        self.options = dict(host=url.hostname, port=url.port or 3306,
                            user=unquote(url.username), password=unquote(url.password or ''),
                            database=unquote(url.path.lstrip('/')), charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor, autocommit=False,
                            connect_timeout=5, read_timeout=15, write_timeout=15)

    @contextmanager
    def transaction(self):
        connection = pymysql.connect(**self.options)
        try:
            with connection.cursor() as cursor:
                cursor.execute('SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED')
                cursor.execute("SET time_zone = '+00:00'")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


class MySQLTaskRepository:
    def __init__(self, connections):
        self.connections = connections

    def list_due(self, now):
        with self.connections.transaction() as connection:
            with connection.cursor() as cursor:
                cursor.execute('''SELECT t.* FROM tasks t JOIN users u ON u.id=t.user_id
                    WHERE t.enabled=TRUE AND u.is_active=TRUE AND t.scheduled_time <= %s
                    AND NOT EXISTS (SELECT 1 FROM task_runs r WHERE r.task_id=t.id AND r.scheduled_date=%s)
                    ORDER BY t.scheduled_time, t.id''', (now.strftime('%H:%M:%S'), now.date()))
                rows = cursor.fetchall()
        return [Task(row['user_id'], (datetime.min + row['scheduled_time']).time(),
                     row['action'], json.loads(row['parameters']), row['id']) for row in rows]


class MySQLRunRepository:
    def __init__(self, connections):
        self.connections = connections

    def claim(self, task, on_date):
        with self.connections.transaction() as connection:
            with connection.cursor() as cursor:
                # Serialisasi seluruh klaim untuk satu user, sebelum menghitung kuota.
                cursor.execute('SELECT daily_quota FROM users WHERE id=%s AND is_active=TRUE FOR UPDATE', (task.user_id,))
                user = cursor.fetchone()
                if not user:
                    raise ValueError('User tidak aktif atau tidak ditemukan')
                cursor.execute('SELECT id FROM tasks WHERE id=%s AND user_id=%s AND enabled=TRUE FOR UPDATE', (task.id, task.user_id))
                if not cursor.fetchone():
                    raise ValueError('Task tidak aktif atau pemilik berubah')
                cursor.execute('SELECT id FROM task_runs WHERE task_id=%s AND scheduled_date=%s', (task.id, on_date))
                if cursor.fetchone():
                    return None
                cursor.execute("SELECT COUNT(*) AS used FROM task_runs WHERE user_id=%s AND scheduled_date=%s AND status <> 'rejected_quota'", (task.user_id, on_date))
                rejected = cursor.fetchone()['used'] >= user['daily_quota']
                run = dict(id=str(uuid4()), status='rejected_quota' if rejected else 'running')
                cursor.execute('''INSERT INTO task_runs
                    (id, task_id, user_id, scheduled_date, status, started_at, finished_at, message)
                    VALUES (%s,%s,%s,%s,%s,IF(%s,NULL,NOW()),IF(%s,NOW(),NULL),%s)''',
                    (run['id'], task.id, task.user_id, on_date, run['status'], rejected, rejected,
                     'Kuota harian habis' if rejected else None))
                return run

    def finish(self, run_id, status, message):
        if status not in ('succeeded', 'failed'):
            raise ValueError('Status akhir tidak valid')
        with self.connections.transaction() as connection:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE task_runs SET status=%s,message=%s,finished_at=NOW() WHERE id=%s AND status='running'", (status, message, run_id))
                if cursor.rowcount != 1:
                    raise ValueError('Run tidak ditemukan atau sudah selesai')


class MySQLTaskExecutor:
    def __init__(self, runs, actions):
        self.runs, self.actions = runs, actions
        self.logger = logging.getLogger(__name__)

    def execute(self, task, on_date):
        try:
            action = self.actions.get(task.action)
            if action is None:
                raise ValueError('Aksi tidak terdaftar')
            run = self.runs.claim(task, on_date)
        except Exception as error:
            self.logger.error('Klaim gagal task_id=%s error_type=%s', task.id, type(error).__name__)
            return TaskResult(task.id, False, 'Klaim gagal; periksa konfigurasi dan database')
        if run is None:
            return TaskResult(task.id, False, 'Task sudah diklaim hari ini')
        if run['status'] == 'rejected_quota':
            self.logger.warning('Kuota habis task_id=%s user=%s', task.id, task.user_id)
            return TaskResult(task.id, False, 'Kuota harian habis')
        try:
            message = action.execute(task.parameters)
            status = 'succeeded'
        except Exception as error:
            status, message = 'failed', 'Action gagal: ' + type(error).__name__
        try:
            self.runs.finish(run['id'], status, message)
        except Exception:
            # Jangan ulangi action: efek sampingnya mungkin sudah terjadi.
            self.logger.error('Hasil belum tersimpan run_id=%s; perlu rekonsiliasi', run['id'])
            return TaskResult(task.id, False, 'Hasil belum tersimpan; perlu rekonsiliasi')
        self.logger.info('Task selesai task_id=%s run_id=%s status=%s', task.id, run['id'], status)
        return TaskResult(task.id, status == 'succeeded', message)


class MySQLDailyScheduler:
    def __init__(self, tasks, executor):
        self.tasks, self.executor = tasks, executor

    def run_pending(self, now=None):
        # Jadwal harian memakai WIB; timestamp audit database disimpan dalam UTC.
        now = now or datetime.now(timezone(timedelta(hours=7)))
        return [self.executor.execute(task, now.date()) for task in self.tasks.list_due(now)]

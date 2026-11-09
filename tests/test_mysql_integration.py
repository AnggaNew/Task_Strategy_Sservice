"""Tes database opt-in; hanya membuat dan menghapus baris dengan UUID milik tes."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from uuid import uuid4


@unittest.skipUnless(os.getenv('TEST_MYSQL') == '1', 'Set TEST_MYSQL=1 untuk tes database lokal')
class MySQLIntegrationTests(unittest.TestCase):
    def setUp(self):
        from dotenv import load_dotenv
        from task_service.mysql import MySQLConnectionFactory, MySQLRunRepository
        from task_service.models import Task
        load_dotenv(Path(__file__).resolve().parents[1] / '.env.mysql')
        self.db = MySQLConnectionFactory()
        self.runs = MySQLRunRepository(self.db)
        self.user_id = str(uuid4())
        self.today = datetime(2026, 11, 9).date()
        self.tasks = [Task(self.user_id, datetime.min.time(), 'sync', {'target': '/test'}, str(uuid4())) for _ in range(2)]
        with self.db.transaction() as connection:
            with connection.cursor() as cursor:
                cursor.execute('INSERT INTO users(id,username,daily_quota) VALUES (%s,%s,1)', (self.user_id, 'test_' + self.user_id))
                for task in self.tasks:
                    cursor.execute('INSERT INTO tasks(id,user_id,scheduled_time,action,parameters) VALUES(%s,%s,%s,%s,%s)',
                                   (task.id, self.user_id, '00:00:00', 'sync', '{"target":"/test"}'))

    def tearDown(self):
        with self.db.transaction() as connection:
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM task_runs WHERE user_id=%s', (self.user_id,))
                cursor.execute('DELETE FROM tasks WHERE user_id=%s', (self.user_id,))
                cursor.execute('DELETE FROM users WHERE id=%s', (self.user_id,))

    def test_same_task_claimed_once_concurrently(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.runs.claim(self.tasks[0], self.today), range(2)))
        self.assertEqual(sum(result is not None for result in results), 1)

    def test_quota_limits_concurrent_tasks(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda task: self.runs.claim(task, self.today), self.tasks))
        self.assertCountEqual([result['status'] for result in results], ['running', 'rejected_quota'])

    def test_action_result_persisted_and_due_mapping(self):
        from task_service.mysql import MySQLTaskRepository, MySQLTaskExecutor
        from task_service.actions import SyncAction
        due = MySQLTaskRepository(self.db).list_due(datetime(2026, 11, 9, 12))
        task = next(task for task in due if task.id == self.tasks[0].id)
        result = MySQLTaskExecutor(self.runs, {'sync': SyncAction()}).execute(task, self.today)
        self.assertTrue(result.success)
        with self.db.transaction() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT status FROM task_runs WHERE task_id=%s', (task.id,))
                self.assertEqual(cursor.fetchone()['status'], 'succeeded')

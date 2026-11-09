from datetime import datetime
import unittest

from task_service.actions import SyncAction
from task_service.executor import TaskExecutor
from task_service.models import Task
from task_service.scheduler import DailyScheduler
from task_service.users import UserManager


class TaskServiceTests(unittest.TestCase):
    def test_multiple_tasks_for_one_user_respect_daily_quota(self):
        users = UserManager({"alice": 1})
        executor = TaskExecutor(users, {"sync": SyncAction()})
        tasks = [
            Task.from_dict({"id": "one", "user": "alice", "time": "12:00", "action": "sync", "target": "/a"}),
            Task.from_dict({"id": "two", "user": "alice", "time": "12:00", "action": "sync", "target": "/b"}),
        ]
        results = DailyScheduler(tasks, executor).run_pending(datetime(2026, 11, 9, 12, 0))
        self.assertEqual([result.success for result in results], [True, False])
        self.assertEqual(users.remaining_quota("alice", datetime(2026, 11, 9).date()), 0)

    def test_task_only_runs_once_per_day_but_resets_next_day(self):
        users = UserManager({"alice": 2})
        executor = TaskExecutor(users, {"sync": SyncAction()})
        scheduler = DailyScheduler([Task.from_dict({"id": "one", "user": "alice", "time": "12:00", "action": "sync", "target": "/a"})], executor)
        self.assertEqual(len(scheduler.run_pending(datetime(2026, 11, 9, 12, 0))), 1)
        self.assertEqual(scheduler.run_pending(datetime(2026, 11, 9, 12, 1)), [])
        self.assertEqual(len(scheduler.run_pending(datetime(2026, 11, 10, 12, 0))), 1)

    def test_invalid_action_returns_error_instead_of_crashing(self):
        users = UserManager({"alice": 1})
        task = Task.from_dict({"user": "alice", "time": "12:00", "action": "unknown", "target": "/a"})
        result = TaskExecutor(users, {}).execute(task, datetime(2026, 11, 9).date())
        self.assertFalse(result.success)
        self.assertIn("tidak terdaftar", result.message)

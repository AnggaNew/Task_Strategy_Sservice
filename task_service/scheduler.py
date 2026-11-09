"""Scheduler polling sederhana yang memastikan setiap task harian berjalan sekali."""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional

from .executor import TaskExecutor
from .models import Task, TaskResult


class DailyScheduler:
    def __init__(self, tasks: List[Task], executor: TaskExecutor) -> None:
        self._tasks = tasks
        self._executor = executor
        self._last_run: Dict[str, date] = {}
        self._logger = logging.getLogger(__name__)

    def run_pending(self, now: Optional[datetime] = None) -> List[TaskResult]:
        now = now or datetime.now()
        results: List[TaskResult] = []
        for task in self._tasks:
            if not task.enabled or task.scheduled_time > now.time() or self._last_run.get(task.id) == now.date():
                continue
            self._logger.info("Menjalankan task terjadwal task_id=%s", task.id)
            results.append(self._executor.execute(task, now.date()))
            # Catat percobaan supaya task yang gagal tidak diputar berulang dalam hari yang sama.
            self._last_run[task.id] = now.date()
        return results

"""Orkestrasi satu eksekusi task dan pencatatan hasilnya."""

import logging
from datetime import date
from typing import Dict

from .actions import ActionStrategy
from .models import Task, TaskResult
from .users import UserManager


class TaskExecutor:
    def __init__(self, users: UserManager, actions: Dict[str, ActionStrategy]) -> None:
        self._users = users
        self._actions = actions
        self._logger = logging.getLogger(__name__)

    def execute(self, task: Task, on_date: date) -> TaskResult:
        try:
            # Validasi konfigurasi sebelum mengonsumsi kuota pengguna.
            action = self._actions.get(task.action)
            if action is None:
                raise ValueError(f"Aksi tidak terdaftar: {task.action}")

            if not self._users.can_execute(task.user_id, on_date):
                message = "Kuota harian telah habis"
                self._logger.warning("Task diblokir quota task_id=%s user=%s", task.id, task.user_id)
                return TaskResult(task.id, False, message)

            message = action.execute(task.parameters)
            self._logger.info("Task berhasil task_id=%s user=%s action=%s", task.id, task.user_id, task.action)
            return TaskResult(task.id, True, message)
        except (KeyError, ValueError) as error:
            self._logger.error("Task gagal task_id=%s: %s", task.id, error)
            return TaskResult(task.id, False, str(error))
        except Exception:
            self._logger.exception("Kesalahan tak terduga saat task_id=%s", task.id)
            return TaskResult(task.id, False, "Kesalahan eksekusi tak terduga")

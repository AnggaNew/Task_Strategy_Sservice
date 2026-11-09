"""Model domain yang tidak bergantung pada cara task dieksekusi."""

from datetime import datetime, time
from typing import Any, Mapping
from uuid import uuid4


class Task:
    """Definisi task yang dijalankan setiap hari pada `scheduled_time`."""

    def __init__(self, user_id, scheduled_time, action, parameters=None, id=None, enabled=True):
        self.user_id = user_id
        self.scheduled_time = scheduled_time
        self.action = action
        self.parameters = dict(parameters or {})
        self.id = id or str(uuid4())
        self.enabled = enabled

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Task":
        """Membuat task dari konfigurasi dan memvalidasi field wajib."""
        required = {"user", "time", "action"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"Konfigurasi task tidak lengkap: {sorted(missing)}")

        try:
            value = str(data["time"])
            format_string = "%H:%M:%S" if value.count(":") == 2 else "%H:%M"
            scheduled_time = datetime.strptime(value, format_string).time()
        except ValueError as error:
            raise ValueError("'time' harus berformat HH:MM atau HH:MM:SS") from error

        # Bentuk lama tetap kompatibel: target masuk ke parameters bila ada.
        parameters = dict(data.get("parameters", {}))
        if "target" in data:
            parameters.setdefault("target", data["target"])

        return cls(
            id=str(data.get("id", uuid4())),
            user_id=str(data["user"]),
            scheduled_time=scheduled_time,
            action=str(data["action"]),
            parameters=parameters,
            enabled=bool(data.get("enabled", True)),
        )


class TaskResult:
    def __init__(self, task_id, success, message):
        self.task_id = task_id
        self.success = success
        self.message = message

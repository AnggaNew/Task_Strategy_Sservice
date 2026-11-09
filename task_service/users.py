"""Manajemen pengguna dan pembatasan kuota eksekusi harian."""

from datetime import date
from threading import Lock
from typing import Dict, Optional


class UserQuota:
    def __init__(self, daily_quota, executed=0, quota_date=None):
        self.daily_quota = daily_quota
        self.executed = executed
        self.quota_date = quota_date


class UserManager:
    """Penyimpanan in-memory; ganti implementasi ini dengan repository/DB di produksi."""

    def __init__(self, user_quotas: Dict[str, int]) -> None:
        if any(quota < 0 for quota in user_quotas.values()):
            raise ValueError("Kuota tidak boleh negatif")
        self._users = {user_id: UserQuota(quota) for user_id, quota in user_quotas.items()}
        self._lock = Lock()

    def can_execute(self, user_id: str, on_date: date) -> bool:
        """Atomically consume one quota if available, lalu kembalikan hasilnya."""
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                raise KeyError(f"Pengguna tidak ditemukan: {user_id}")
            if user.quota_date != on_date:
                user.executed = 0
                user.quota_date = on_date
            if user.executed >= user.daily_quota:
                return False
            user.executed += 1
            return True

    def remaining_quota(self, user_id: str, on_date: date) -> int:
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                raise KeyError(f"Pengguna tidak ditemukan: {user_id}")
            executed = user.executed if user.quota_date == on_date else 0
            return max(0, user.daily_quota - executed)

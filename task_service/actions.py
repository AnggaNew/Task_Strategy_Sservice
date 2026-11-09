"""Strategi aksi. Aksi baru cukup mengimplementasikan ActionStrategy lalu didaftarkan."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Mapping


class ActionStrategy(ABC):
    @abstractmethod
    def execute(self, parameters: Mapping[str, Any]) -> str:
        """Jalankan aksi dan kembalikan deskripsi hasilnya; lempar exception saat gagal."""


class SyncAction(ActionStrategy):
    def execute(self, parameters: Mapping[str, Any]) -> str:
        target = _required_target(parameters)
        logging.getLogger(__name__).info("Menyinkronkan target=%s", target)
        return f"Sinkronisasi selesai: {target}"


class BackupAction(ActionStrategy):
    def execute(self, parameters: Mapping[str, Any]) -> str:
        target = _required_target(parameters)
        logging.getLogger(__name__).info("Mencadangkan target=%s", target)
        return f"Pencadangan selesai: {target}"


class DeleteAction(ActionStrategy):
    def execute(self, parameters: Mapping[str, Any]) -> str:
        # Contoh aman: aksi nyata harus mendapat validasi/otorisasi tambahan.
        target = _required_target(parameters)
        logging.getLogger(__name__).warning("Permintaan hapus diterima untuk target=%s", target)
        return f"Penghapusan tersimulasi: {target}"


def _required_target(parameters: Mapping[str, Any]) -> str:
    target = parameters.get("target")
    if not isinstance(target, str) or not target:
        raise ValueError("Parameter 'target' wajib berupa string yang tidak kosong")
    return target

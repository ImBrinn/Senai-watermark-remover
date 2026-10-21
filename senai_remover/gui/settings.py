"""Choices that are remembered between launches: the theme and the
appearance (match the system, or always light or dark).

Stored with QSettings as an INI file, on Windows in
%APPDATA%\\SenAI\\Watermark Remover.ini. SENAI_SETTINGS_FILE points it
somewhere else (the tests use a temporary file).
"""

from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import QSettings

APPEARANCES = ("system", "light", "dark")


class Settings:
    def __init__(self, path: Optional[str] = None):
        path = path or os.environ.get("SENAI_SETTINGS_FILE")
        if path:
            self._store = QSettings(path, QSettings.IniFormat)
        else:
            self._store = QSettings(QSettings.IniFormat, QSettings.UserScope, "SenAI", "Watermark Remover")

    @property
    def theme(self) -> str:
        return str(self._store.value("theme", ""))

    @theme.setter
    def theme(self, theme_id: str) -> None:
        self._store.setValue("theme", theme_id)
        self._store.sync()

    @property
    def appearance(self) -> str:
        value = str(self._store.value("appearance", "system"))
        return value if value in APPEARANCES else "system"

    @appearance.setter
    def appearance(self, value: str) -> None:
        if value not in APPEARANCES:
            raise ValueError(f"appearance must be one of {APPEARANCES}")
        self._store.setValue("appearance", value)
        self._store.sync()

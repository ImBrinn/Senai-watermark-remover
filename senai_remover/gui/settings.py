"""Choices that are remembered between launches: the theme, the
appearance (match the system, or always light or dark), the title put on
page 1 and what cleaned copies are called.

Stored with QSettings as an INI file, on Windows in
%APPDATA%\\SenAI\\Watermark Remover.ini. SENAI_SETTINGS_FILE points it
somewhere else (the tests use a temporary file).
"""

from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import QSettings

from ..core import DEFAULT_NAME, DEFAULT_TITLE, name_problem, title_problem

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

    @property
    def title(self) -> str:
        """The title put where SenAI's was on page 1; "" for none."""
        value = self._store.value("title", DEFAULT_TITLE)
        value = "" if value is None else str(value)
        return value if title_problem(value) is None else DEFAULT_TITLE

    @title.setter
    def title(self, title: str) -> None:
        problem = title_problem(title)
        if problem is not None:
            raise ValueError(problem)
        self._store.setValue("title", title)
        self._store.sync()

    @property
    def output_name(self) -> str:
        """What cleaned copies are called, with {name} for the original name."""
        value = str(self._store.value("output_name", DEFAULT_NAME))
        return value if name_problem(value) is None else DEFAULT_NAME

    @output_name.setter
    def output_name(self, template: str) -> None:
        problem = name_problem(template)
        if problem is not None:
            raise ValueError(problem)
        self._store.setValue("output_name", template)
        self._store.sync()

"""Connects the session to Qt: the list model, and cleaning on a worker thread."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    QThread,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices

from ..core import output_name
from .model import AddResult, FileJob, RunSummary, Session, Status, run_job, summarize

JOB_ROLE = Qt.UserRole + 1


class FileListModel(QAbstractListModel):
    def __init__(self, session: Session, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.session = session

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.session.jobs)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.session.jobs):
            return None
        job = self.session.jobs[index.row()]
        if role == Qt.DisplayRole:
            return job.name
        if role == JOB_ROLE:
            return job
        if role == Qt.ToolTipRole:
            lines = [str(job.source)]
            if job.output is not None:
                lines.append(f"Saved as {job.output}")
            lines += [line for line in (job.message, job.detail) if line]
            return "\n".join(lines)
        if role == Qt.AccessibleTextRole:
            return job.accessible_text()
        return None

    def flags(self, index: QModelIndex):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable if index.isValid() else Qt.NoItemFlags


class _Worker(QObject):
    started_job = Signal(int)
    finished_job = Signal(int)
    done = Signal()

    def __init__(self, plan: list[tuple[int, FileJob, Path]]):
        super().__init__()
        self.plan = plan

    @Slot()
    def run(self) -> None:
        for row, job, target in self.plan:
            self.started_job.emit(row)
            run_job(job, target)
            self.finished_job.emit(row)
        self.done.emit()


class Controller(QObject):
    """Owns the session and outlives any one window, so switching designs
    keeps the file list and results."""

    running_changed = Signal(bool)
    progress = Signal(int, int)  # files done, total
    finished = Signal(object)  # RunSummary
    output_changed = Signal()
    name_changed = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.session = Session()
        self.model = FileListModel(self.session, self)
        self.last_dir = Path.home()
        self.last_summary: Optional[RunSummary] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[_Worker] = None
        self._done = 0

    # File list ---------------------------------------------------------------

    @property
    def jobs(self) -> list[FileJob]:
        return self.session.jobs

    @property
    def running(self) -> bool:
        return self._thread is not None

    def add_paths(self, paths: Iterable[Path]) -> AddResult:
        if self.running:
            return AddResult()
        first = len(self.jobs)
        result = self.session.add(paths)
        if result.added:
            self.model.beginInsertRows(QModelIndex(), first, first + result.added - 1)
            self.model.endInsertRows()
        return result

    def remove_rows(self, rows: Iterable[int]) -> None:
        if self.running:
            return
        rows = sorted({r for r in rows if 0 <= r < len(self.jobs)}, reverse=True)
        for row in rows:
            self.model.beginRemoveRows(QModelIndex(), row, row)
            self.session.remove([row])
            self.model.endRemoveRows()

    def clear(self) -> None:
        if self.running or not self.jobs:
            return
        self.model.beginResetModel()
        self.session.clear()
        self.model.endResetModel()
        self.last_summary = None

    def set_output_dir(self, folder: Optional[Path]) -> None:
        self.session.output_dir = folder
        self.output_changed.emit()

    @property
    def output_dir(self) -> Optional[Path]:
        return self.session.output_dir

    def set_name_template(self, template: str) -> None:
        """Name cleaned copies by ``template`` ({name} is the original name)."""
        if template != self.session.name_template:
            self.session.name_template = template
            self.name_changed.emit()

    @property
    def name_template(self) -> str:
        return self.session.name_template

    def example_name(self, original: str = "name") -> str:
        """What a file called ``original`` would be saved as, e.g. "name-clean.pdf"."""
        return output_name(f"{original}.pdf", self.session.name_template)

    # Cleaning ----------------------------------------------------------------

    def run(self) -> None:
        if self.running or not self.jobs:
            return
        plan = [(row, job, target) for row, (job, target) in enumerate(self.session.plan())]
        for _, job, _ in plan:
            job.status = Status.READY
        self.model.dataChanged.emit(self.model.index(0), self.model.index(len(self.jobs) - 1))
        self._done = 0
        self.last_summary = None

        self._thread = QThread(self)
        self._worker = _Worker(plan)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.started_job.connect(self._row_changed)
        self._worker.finished_job.connect(self._job_done)
        self._worker.done.connect(self._finish)
        self.running_changed.emit(True)
        self.progress.emit(0, len(plan))
        self._thread.start()

    def wait(self) -> None:
        """Block until a run in progress finishes (used when closing)."""
        if self._thread is not None:
            self._thread.wait()

    @Slot(int)
    def _row_changed(self, row: int) -> None:
        index = self.model.index(row)
        self.model.dataChanged.emit(index, index)

    @Slot(int)
    def _job_done(self, row: int) -> None:
        self._row_changed(row)
        self._done += 1
        self.progress.emit(self._done, len(self.jobs))

    @Slot()
    def _finish(self) -> None:
        thread, worker = self._thread, self._worker
        self._thread = self._worker = None
        thread.quit()
        thread.wait()
        worker.deleteLater()
        thread.deleteLater()
        self.last_summary = summarize(self.jobs)
        self.running_changed.emit(False)
        self.finished.emit(self.last_summary)

    # Results -----------------------------------------------------------------

    def outputs(self) -> list[Path]:
        return self.session.outputs()

    def show_outputs(self, rows: Iterable[int] = ()) -> None:
        """Open the folder holding the cleaned copies, selecting the file
        when there's just one (Explorer only)."""
        chosen = [self.jobs[r].output for r in rows if 0 <= r < len(self.jobs)]
        outputs = [p for p in chosen if p is not None] or self.outputs()
        if not outputs:
            return
        if len(outputs) == 1 and sys.platform.startswith("win") and outputs[0].exists():
            subprocess.Popen(["explorer", "/select,", str(outputs[0])])
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(outputs[0].parent)))

    def open_output(self, row: int) -> None:
        if 0 <= row < len(self.jobs) and self.jobs[row].output is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.jobs[row].output)))

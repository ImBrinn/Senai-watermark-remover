"""State behind the desktop app, with no Qt in it.

The file list, each file's status, where cleaned copies go, and the
wording people see for results and errors all live here so every design
shares them and they can be tested without a display.
"""

from __future__ import annotations

import errno
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional

from pypdf.errors import FileNotDecryptedError, PyPdfError

from ..cli import find_pdfs
from ..core import clean_pdf

SUFFIX = "_clean"


class Status(Enum):
    READY = "ready"
    WORKING = "working"
    CLEANED = "cleaned"
    UNCHANGED = "unchanged"
    FAILED = "failed"


@dataclass
class FileJob:
    source: Path
    status: Status = Status.READY
    removed: int = 0
    output: Optional[Path] = None
    # One line for people, plus the technical detail for a tooltip.
    message: str = ""
    detail: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.source.name

    @property
    def folder(self) -> Path:
        return self.source.parent

    def status_text(self) -> tuple[str, str]:
        """(status, secondary) as shown at the end of the file's row."""
        if self.status is Status.WORKING:
            return "Cleaning…", ""
        if self.status is Status.CLEANED:
            extra = f"{self.removed} removed"
            if self.warnings:
                extra += f" · {plural(len(self.warnings), 'warning')}"
            return "Cleaned", extra
        if self.status is Status.UNCHANGED:
            return "Nothing to remove", ""
        if self.status is Status.FAILED:
            return "Couldn't clean", ""
        return "Ready", ""

    def accessible_text(self) -> str:
        status, extra = self.status_text()
        parts = [self.name, f"in {self.folder}", status, extra, self.message]
        return ", ".join(p for p in parts if p)


@dataclass
class AddResult:
    added: int = 0
    duplicates: int = 0
    ignored: int = 0  # not a PDF, or doesn't exist

    def text(self) -> str:
        """A note for anything that wasn't added, or "" when all went in."""
        notes = []
        if self.ignored:
            notes.append(f"{plural(self.ignored, 'item')} skipped: only PDF files can be added")
        if self.duplicates:
            notes.append(f"{plural(self.duplicates, 'PDF')} already in the list")
        return "; ".join(notes)


@dataclass
class RunSummary:
    cleaned: int = 0
    unchanged: int = 0
    failed: int = 0
    outputs: list[Path] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.cleaned + self.unchanged + self.failed

    def text(self) -> str:
        parts = []
        for count, what in ((self.cleaned, "cleaned"),
                            (self.unchanged, "had nothing to remove"),
                            (self.failed, "couldn't be cleaned")):
            if count:
                parts.append(f"{count if parts else plural(count, 'PDF')} {what}")
        return ", ".join(parts) or "Nothing to clean"


class Session:
    """The list of PDFs and where their cleaned copies go."""

    def __init__(self) -> None:
        self.jobs: list[FileJob] = []
        # None means next to each original.
        self.output_dir: Optional[Path] = None

    def add(self, paths: Iterable[Path]) -> AddResult:
        result = AddResult()
        known = {_key(job.source) for job in self.jobs}
        for path in paths:
            path = Path(path)
            if path.is_dir():
                candidates = list(find_pdfs([path], skip_suffix=SUFFIX))
            elif path.is_file() and path.suffix.lower() == ".pdf":
                candidates = [path]
            else:
                result.ignored += 1
                continue
            for pdf in candidates:
                key = _key(pdf)
                if key in known:
                    result.duplicates += 1
                    continue
                known.add(key)
                self.jobs.append(FileJob(pdf.resolve()))
                result.added += 1
        return result

    def remove(self, rows: Iterable[int]) -> list[int]:
        """Remove the given rows; returns them highest first, as removed."""
        rows = sorted({r for r in rows if 0 <= r < len(self.jobs)}, reverse=True)
        for row in rows:
            del self.jobs[row]
        return rows

    def clear(self) -> None:
        self.jobs.clear()

    def plan(self) -> list[tuple[FileJob, Path]]:
        """Each job with the path its cleaned copy will be written to.

        Copies are always named ``name_clean.pdf`` so an original, or an
        unrelated file in the chosen folder, is never overwritten. Two
        files with the same name going to one folder get " (2)", " (3)".
        """
        sources = {_key(job.source) for job in self.jobs}
        taken: set[str] = set()
        planned = []
        for job in self.jobs:
            folder = self.output_dir or job.folder
            stem = f"{job.source.stem}{SUFFIX}"
            target = folder / f"{stem}.pdf"
            n = 2
            while _key(target) in taken or _key(target) in sources:
                target = folder / f"{stem} ({n}).pdf"
                n += 1
            taken.add(_key(target))
            planned.append((job, target))
        return planned

    def outputs(self) -> list[Path]:
        return [job.output for job in self.jobs if job.output is not None]


def run_job(job: FileJob, target: Path) -> None:
    """Clean one file, recording the outcome on the job."""
    job.status = Status.WORKING
    job.message = job.detail = ""
    job.warnings = []
    job.output = None
    try:
        result = clean_pdf(job.source, target)
    except Exception as exc:  # shown on the file's row
        job.status = Status.FAILED
        job.removed = 0
        job.message, job.detail = friendly_error(exc, job.source, target)
        return
    job.output = target
    job.removed = len(result.removed)
    job.warnings = list(result.warnings)
    job.detail = "\n".join(result.warnings)
    job.status = Status.CLEANED if result.changed else Status.UNCHANGED
    if not result.changed:
        job.message = "No SenAI title or footer found. An unchanged copy was saved."


def summarize(jobs: Iterable[FileJob]) -> RunSummary:
    summary = RunSummary()
    for job in jobs:
        if job.status is Status.CLEANED:
            summary.cleaned += 1
        elif job.status is Status.UNCHANGED:
            summary.unchanged += 1
        elif job.status is Status.FAILED:
            summary.failed += 1
        if job.output is not None:
            summary.outputs.append(job.output)
    return summary


def friendly_error(exc: BaseException, source: Path, target: Path) -> tuple[str, str]:
    """(what went wrong and what to do, technical detail) for a failed file."""
    detail = f"{type(exc).__name__}: {exc}"
    filename = getattr(exc, "filename", None)
    about_target = filename is not None and _key(Path(filename)) == _key(target)

    if isinstance(exc, FileNotDecryptedError) or (
        isinstance(exc, ValueError) and "password" in str(exc).lower()
    ):
        return "This PDF is password protected, so it can't be cleaned.", detail
    if isinstance(exc, PermissionError):
        if about_target:
            return (f"Couldn't save {target.name}. If it's open in a PDF viewer, "
                    "close it and try again."), detail
        return "Couldn't open this file. If it's open in another app, close it and try again.", detail
    if isinstance(exc, FileNotFoundError):
        if about_target:
            return "Couldn't save to that folder. It may have been moved or deleted.", detail
        return "This file has been moved or deleted.", detail
    if isinstance(exc, OSError) and exc.errno == errno.ENOSPC:
        return "There isn't enough disk space to save the cleaned copy.", detail
    if isinstance(exc, PyPdfError):
        return "This file isn't a readable PDF.", detail
    return "Couldn't clean this file.", detail


def plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _key(path: Path) -> str:
    # normcase folds case on Windows, where paths are case-insensitive, so
    # duplicates and name collisions can't slip through as "different".
    return os.path.normcase(str(Path(path).resolve()))

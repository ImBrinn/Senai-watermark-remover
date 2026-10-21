"""Small desktop window: add PDFs, choose where to save, click Remove."""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Iterable, Optional, Sequence

from .cli import describe, find_pdfs
from .core import clean_pdf, default_output_path


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.files: list[Path] = []
        self.events: queue.Queue = queue.Queue()
        self.output_mode = tk.StringVar(value="beside")
        self.output_dir = tk.StringVar()
        self.last_folder: Optional[Path] = None
        self.busy = False

        root.title("SenAI Watermark Remover")
        root.minsize(580, 480)
        frame = ttk.Frame(root, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame, text='Removes the "SenAI Maths" title and the senai.uk footer from PDFs.'
        ).pack(anchor="w")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(10, 4))
        self.add_files_btn = ttk.Button(buttons, text="Add PDFs…", command=self.pick_files)
        self.add_folder_btn = ttk.Button(buttons, text="Add folder…", command=self.pick_folder)
        self.remove_btn = ttk.Button(buttons, text="Remove selected", command=self.remove_selected)
        self.clear_btn = ttk.Button(buttons, text="Clear", command=self.clear)
        for button in (self.add_files_btn, self.add_folder_btn, self.remove_btn, self.clear_btn):
            button.pack(side="left", padx=(0, 6))

        listing = ttk.Frame(frame)
        listing.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(listing, selectmode="extended", height=8, activestyle="none")
        scrollbar = ttk.Scrollbar(listing, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        save = ttk.LabelFrame(frame, text="Save cleaned PDFs", padding=8)
        save.pack(fill="x", pady=10)
        ttk.Radiobutton(
            save, text="Next to the original (name_clean.pdf)",
            variable=self.output_mode, value="beside",
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Radiobutton(save, text="In folder:", variable=self.output_mode, value="folder").grid(
            row=1, column=0, sticky="w"
        )
        self.folder_entry = ttk.Entry(save, textvariable=self.output_dir)
        self.folder_entry.grid(row=1, column=1, sticky="ew", padx=6)
        self.browse_btn = ttk.Button(save, text="Browse…", command=self.pick_output_dir)
        self.browse_btn.grid(row=1, column=2)
        save.columnconfigure(1, weight=1)

        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        self.run_btn = ttk.Button(actions, text="Remove watermark", command=self.start)
        self.run_btn.pack(side="left")
        self.open_btn = ttk.Button(
            actions, text="Open output folder", command=self.open_output, state="disabled"
        )
        self.open_btn.pack(side="right")
        self.progress = ttk.Progressbar(actions, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=8)

        self.log_box = ScrolledText(frame, height=8, state="disabled", wrap="word")
        self.log_box.pack(fill="both", expand=True, pady=(10, 0))

    # File list ---------------------------------------------------------------

    def add_paths(self, paths: Iterable[Path]) -> None:
        for path in find_pdfs(paths, skip_suffix="_clean"):
            path = path.resolve()
            if path not in self.files:
                self.files.append(path)
                self.listbox.insert("end", f"{path.name}    ({path.parent})")

    def pick_files(self) -> None:
        names = filedialog.askopenfilenames(
            title="Choose PDFs", filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        self.add_paths(Path(n) for n in names)

    def pick_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose a folder of PDFs")
        if folder:
            self.add_paths([Path(folder)])

    def pick_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="Save cleaned PDFs in…")
        if folder:
            self.output_dir.set(folder)
            self.output_mode.set("folder")

    def remove_selected(self) -> None:
        for index in reversed(self.listbox.curselection()):
            self.listbox.delete(index)
            del self.files[index]

    def clear(self) -> None:
        self.listbox.delete(0, "end")
        self.files.clear()

    # Processing --------------------------------------------------------------

    def start(self) -> None:
        if not self.files:
            messagebox.showinfo("Nothing to do", "Add some PDFs first.")
            return
        output_dir = None
        if self.output_mode.get() == "folder":
            if not self.output_dir.get().strip():
                messagebox.showinfo("Choose a folder", "Pick a folder to save the cleaned PDFs in.")
                return
            output_dir = Path(self.output_dir.get().strip())

        jobs = [(source, default_output_path(source, output_dir)) for source in self.files]
        clashes = [s.name for s, t in jobs if t.resolve() == s.resolve()]
        if clashes:
            messagebox.showerror(
                "Would overwrite originals",
                "The output folder is the same folder as these files:\n" + "\n".join(clashes)
                + "\n\nChoose a different folder or save next to the original.",
            )
            return

        self.set_busy(True)
        self.progress.configure(maximum=len(jobs), value=0)
        threading.Thread(target=self.work, args=(jobs,), daemon=True).start()
        self.root.after(100, self.poll)

    def work(self, jobs: list[tuple[Path, Path]]) -> None:
        """Runs on a worker thread; talks to the UI only through ``self.events``."""
        cleaned = 0
        for source, target in jobs:
            try:
                result = clean_pdf(source, target)
                if result.changed:
                    cleaned += 1
                    self.events.put(("log", f"✓ {source.name} → {target.name}  (removed {describe(result)})"))
                else:
                    self.events.put(("log", f"– {source.name}: no SenAI branding found (copy saved as {target.name})"))
                for warning in result.warnings:
                    self.events.put(("log", f"   ⚠ {warning}"))
            except Exception as exc:
                self.events.put(("log", f"✗ {source.name}: {exc}"))
            self.events.put(("step", target.parent))
        self.events.put(("log", f"Done: cleaned {cleaned} of {len(jobs)} file(s).\n"))
        self.events.put(("done", None))

    def poll(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self.log(value)
                elif kind == "step":
                    self.progress["value"] += 1
                    self.last_folder = value
                elif kind == "done":
                    self.set_busy(False)
        except queue.Empty:
            pass
        if self.busy:
            self.root.after(100, self.poll)

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        for widget in (self.add_files_btn, self.add_folder_btn, self.remove_btn,
                       self.clear_btn, self.browse_btn, self.run_btn):
            widget.configure(state=state)
        self.open_btn.configure(state="normal" if not busy and self.last_folder else "disabled")

    def log(self, line: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def open_output(self) -> None:
        if self.last_folder:
            open_folder(self.last_folder)


def open_folder(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Open the window, pre-loaded with any PDFs passed as arguments."""
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    if sys.platform.startswith("win"):
        try:  # crisp text on high-DPI screens
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    app = App(root)
    app.add_paths(Path(a) for a in (argv if argv is not None else sys.argv[1:]) if Path(a).exists())
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

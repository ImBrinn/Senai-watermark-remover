# Changelog

All notable changes to SenAI Watermark Remover are listed here, newest first.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [2.1.0] - 2026-10-21

### Added
- **Settings panel** that slides in from the right. Open it with the gear button in every theme, from the menus, or with <kbd>Ctrl</kbd>+<kbd>,</kbd>.
- **Theme preview cards** in Settings: click one to switch instantly. The file list and results carry over.
- **Appearance setting**: Match system, Light or Dark.
- Theme and appearance are **saved** and restored at the next launch (`%APPDATA%\SenAI\Watermark Remover.ini`).
- **Release workflow** that builds and publishes the Windows `.exe` for every tag.
- **Claude Code project setup**: `CLAUDE.md`, a SessionStart hook that installs dependencies in cloud sessions, and `/build-exe`, `/release` and `/screenshots` project skills.
- This changelog.

### Changed
- The four design prototypes are now **themes**: Apple Classic, Apple Liquid Glass, Exercise Book and Windows 11 Fluent.
- **Rewritten README** with screenshots of every theme in light and dark, a download section, shortcuts and troubleshooting.

## [2.0.0] - 2026-10-21

### Changed
- The desktop app is **rebuilt with Qt 6.8 (PySide6)**, replacing the Tkinter window. The command line still needs only pypdf.

### Added
- **Four design prototypes**, switchable with <kbd>Ctrl</kbd>+<kbd>1</kbd> to <kbd>Ctrl</kbd>+<kbd>4</kbd>: Apple Classic, Apple Liquid Glass, Exercise Book and Windows 11 Fluent.
- **Drag and drop** of PDFs or whole folders onto the window.
- **Per-file results** on each row: Cleaned with the number of items removed, Nothing to remove, or Couldn't clean.
- **Plain-language errors**, for example "Couldn't save x_clean.pdf. If it's open in a PDF viewer, close it and try again."
- **Keyboard shortcuts**: <kbd>Ctrl</kbd>+<kbd>O</kbd>, <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>O</kbd>, <kbd>Ctrl</kbd>+<kbd>Enter</kbd> and <kbd>Delete</kbd>.
- **Light and dark mode** that follow Windows, with every declared text colour pair tested at 4.5:1 contrast or better.
- **Safe output names**: cleaned copies are always `name_clean.pdf`, and two files with the same name going to one folder get " (2)", " (3)", so an original is never overwritten.
- A new **app icon**, plus the bundled Inter typeface and Lucide icons.

## [1.0.0] - 2026-10-21

### Added
- **First release.** Removes the "SenAI Maths" title on page 1 and the senai.uk footer on every page of SenAI Maths PDFs, along with senai.uk links and document metadata that mention SenAI.
- The branding text is **deleted from the PDF's content stream** rather than covered up. Answers, working, diagrams and page numbers are untouched.
- **Desktop window** (Tkinter) for picking files or a folder and saving cleaned copies as `name_clean.pdf`.
- **Command line** (`senai-remover`) for files and folders, with `-o`, `--in-place`, `--suffix` and `--pattern`.
- A single-file **Windows `.exe`**.

[2.1.0]: https://github.com/ImBrinn/Senai-watermark-remover/releases/tag/v2.1.0
[2.0.0]: https://github.com/ImBrinn/Senai-watermark-remover/releases/tag/v2.0.0
[1.0.0]: https://github.com/ImBrinn/Senai-watermark-remover/releases/tag/v1.0.0

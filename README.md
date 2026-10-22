<p align="center">
  <img src="senai_remover/gui/assets/app.png" width="128" height="128" alt="SenAI Watermark Remover app icon: a page and an eraser">
</p>

<h1 align="center">SenAI Watermark Remover</h1>

<p align="center">
  <strong>Clean copies of your SenAI Maths PDFs: your own title instead of “SenAI Maths”, no senai.uk footer, and SenAI’s broken symbols and squashed sentences fixed.</strong><br>
  Drop your PDFs in, press one button, and get clean copies. Your answers and working stay exactly as they were.
</p>

<p align="center">
  <a href="https://github.com/ImBrinn/Senai-watermark-remover/releases/latest"><img src="https://img.shields.io/badge/Download-latest%20release-2ea44f?logo=github&logoColor=white" alt="Download the latest release"></a>
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows&logoColor=white" alt="Windows 10 and 11">
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" alt="Python 3.9 or newer">
  <img src="https://img.shields.io/badge/Qt-6.8%20(PySide6)-41CD52?logo=qt&logoColor=white" alt="Qt 6.8 via PySide6">
</p>

<p align="center">
  <a href="https://github.com/ImBrinn/Senai-watermark-remover/releases/latest/download/SenAI-Watermark-Remover.exe"><strong>⬇&nbsp;Download for Windows</strong></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/ImBrinn/Senai-watermark-remover/releases">All releases</a>
  &nbsp;·&nbsp;
  <a href="CHANGELOG.md">What’s new</a>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/apple-classic-dark.png">
    <img src="docs/screenshots/apple-classic-light.png" width="820" alt="SenAI Watermark Remover showing a list of PDFs and the result for each one">
  </picture>
</p>

---

## Contents

- [Highlights](#highlights)
- [Download](#download)
- [How to use it](#how-to-use-it)
- [Themes](#themes)
- [Settings](#settings)
- [Keyboard shortcuts](#keyboard-shortcuts)
- [What changes](#what-changes)
- [Troubleshooting](#troubleshooting)
- [Command line](#command-line)
- [How it works](#how-it-works)
- [Accessibility](#accessibility)
- [Building from source](#building-from-source)
- [Code signing policy](#code-signing-policy)
- [Credits and licences](#credits-and-licences)

## Highlights

- **Your title, not SenAI’s.** “SenAI Maths” at the top of page 1 becomes **Brinns autocompleter**, or a title of your own from Settings, in the same place, size and style. The senai.uk footer is deleted from the PDF itself, not hidden under a white box.
- **Fixes SenAI’s typesetting.** Empty boxes where SenAI’s PDFs lose a symbol become proper degree signs (180°), multiplication dots (2 · 3) and arrows (⇒), and sentences printed with no spaces (“Anisoscelestriangle…”) are set again with their spaces.
- **Never touches your originals.** Cleaned copies are saved as `name-clean.pdf`, next to the originals or in a folder you choose. You can change the name in Settings.
- **Drag and drop.** Drop single PDFs or a whole folder onto the window.
- **Clear results.** Every file gets its own result and, when something goes wrong, a plain-language reason.
- **Four themes.** Apple Classic, Apple Liquid Glass, Exercise Book and Windows 11 Fluent, each in light and dark.
- **Private.** Everything runs on your computer. Your files are never uploaded anywhere.
- **No install.** One `.exe`, about 42 MB.

## Download

1. Download **[SenAI-Watermark-Remover.exe](https://github.com/ImBrinn/Senai-watermark-remover/releases/latest/download/SenAI-Watermark-Remover.exe)** from the [latest release](https://github.com/ImBrinn/Senai-watermark-remover/releases/latest).
2. Double-click it. There’s nothing to install.
3. If Windows SmartScreen says it protected your PC, choose **More info → Run anyway**. It shows that warning because the app isn’t code-signed.

Older versions are on the [releases page](https://github.com/ImBrinn/Senai-watermark-remover/releases), and the [changelog](CHANGELOG.md) lists what changed in each.

## How to use it

| | |
|---|---|
| **1. Add your PDFs** | Drag PDFs or a whole folder onto the window, or use **Add Files…** / **Add Folder…**. |
| **2. Remove the watermarks** | Click **Remove Watermarks** or press <kbd>Ctrl</kbd>+<kbd>Enter</kbd>. |
| **3. Check each file** | Each row shows its result: **Cleaned · 9 removed · 12 fixed**, **Nothing to remove**, or **Couldn’t clean** with the reason. |
| **4. Open the results** | **Show in Folder** opens where the cleaned copies were saved. |

Cleaned copies are named `name-clean.pdf` unless you choose another name in [Settings](#settings). If two files with the same name go to one folder, the second becomes `name-clean (2).pdf`, then ` (3)`, and so on, so nothing is overwritten.

## Themes

Pick a theme in **Settings**, or switch instantly with <kbd>Ctrl</kbd>+<kbd>1</kbd> to <kbd>Ctrl</kbd>+<kbd>4</kbd>. Your file list and results carry over. Every theme comes in light and dark. The screenshots below follow your GitHub appearance.

<table>
  <tr>
    <td width="50%" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/apple-classic-dark.png">
        <img src="docs/screenshots/apple-classic-light.png" width="400" alt="Apple Classic theme: menu bar, symbol toolbar, inset list and status bar">
      </picture>
      <p><strong>1 · Apple Classic</strong><br>
      A Mac-style window that follows Apple’s Human Interface Guidelines: a menu bar with every command, a symbol toolbar with one prominent action, an inset list and a status bar.</p>
    </td>
    <td width="50%" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/apple-glass-dark.png">
        <img src="docs/screenshots/apple-glass-light.png" width="400" alt="Apple Liquid Glass theme: floating glass toolbar capsules above a list of file cards">
      </picture>
      <p><strong>2 · Apple Liquid Glass</strong><br>
      Apple’s current design language: floating glass toolbar capsules over files that blur as they scroll underneath, with a solid fallback when Windows transparency effects are off.</p>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/exercise-book-dark.png">
        <img src="docs/screenshots/exercise-book-light.png" width="400" alt="Exercise Book theme: squared maths paper with a red margin, a highlighted row and hand-drawn ticks">
      </picture>
      <p><strong>3 · Exercise Book</strong><br>
      Squared maths paper with a red margin, highlighter selection, hand-drawn ticks and a teacher’s score like “3/4”. In dark mode it becomes a chalkboard.</p>
    </td>
    <td width="50%" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/fluent-dark.png">
        <img src="docs/screenshots/fluent-light.png" width="400" alt="Windows 11 Fluent theme: command bar, a card holding the file list and an InfoBar message">
      </picture>
      <p><strong>4 · Windows 11 Fluent</strong><br>
      A native Windows 11 look: a command bar, cards, InfoBar messages and Segoe UI.</p>
    </td>
  </tr>
</table>

## Settings

Open Settings with the gear button in any theme, from the menus, or with <kbd>Ctrl</kbd>+<kbd>,</kbd>. A panel slides in from the right with:

- **Theme**: the four themes as preview cards. Click one to switch instantly.
- **Appearance**: **Match system**, **Light** or **Dark**.
- **Title**: what goes where “SenAI Maths” was on page 1. It starts as **Brinns autocompleter**. Leave it empty for no title, or press **Reset** to go back. A long title is made smaller to fit the page.
- **Cleaned copies**: what the cleaned copies are called. `{name}` stands for the original file’s name, so the default `{name}-clean` turns `Week 3.pdf` into `Week 3-clean.pdf`. Try `{name} (Brinn)` or `Brinn - {name}`. An example updates as you type, and a name Windows wouldn’t allow is pointed out straight away.

Your choices are saved and restored next time, in `%APPDATA%\SenAI\Watermark Remover.ini`.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/settings-dark.png">
    <img src="docs/screenshots/settings-light.png" width="820" alt="The settings panel open on the right, showing the four theme preview cards, the Appearance choice, the title for page 1 and the name for cleaned copies">
  </picture>
</p>

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| <kbd>Ctrl</kbd>+<kbd>O</kbd> | Add files |
| <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>O</kbd> | Add a folder |
| <kbd>Ctrl</kbd>+<kbd>Enter</kbd> | Remove watermarks |
| <kbd>Delete</kbd> | Remove the selected files from the list |
| <kbd>Ctrl</kbd>+<kbd>,</kbd> | Open Settings |
| <kbd>Ctrl</kbd>+<kbd>1</kbd> … <kbd>Ctrl</kbd>+<kbd>4</kbd> | Switch theme |
| <kbd>Ctrl</kbd>+<kbd>Q</kbd> | Exit |

In **Apple Liquid Glass**, tap <kbd>Alt</kbd> to show the menu bar.

## What changes

<p align="center">
  <img src="docs/screenshots/before-after.png" width="820" alt="A SenAI page before and after cleaning. Before: the title SenAI Maths, gaps where degree signs, a multiplication dot and an arrow should be, and two sentences in italic with no spaces. After: the title Brinns autocompleter, 180°, 2 · 3 and the arrow drawn, and the sentences set normally with spaces.">
</p>

| Changed | Kept exactly as it was |
|---|---|
| The **“SenAI Maths”** title becomes **Brinns autocompleter**, in the same place, size and style | Questions, answers and working |
| The **senai.uk** footer on every page is removed | Diagrams and images |
| Links to senai.uk and metadata that mentions SenAI are removed | Page numbers |
| **Empty boxes** become the symbols SenAI lost: degree signs, multiplication dots and the ⇒ arrow | Maths that SenAI set correctly |
| **Sentences with no spaces** are set again with their spaces, in the page’s own font | Your original file, which is never changed |
| The document title in your PDF viewer is the file’s name instead of “about:blank” | |

Nothing else is added: the title is the only new text on the page.

<details>
<summary><strong>How are the spaces put back?</strong></summary>

<br>

SenAI sometimes writes a sentence as maths, so every letter is printed on its own and the spaces are lost. The app reads the letters back, splits them into English words using a list of about 126,000 words ordered by how common they are, and only rewrites the line if every piece is a real word. A line it can’t read with confidence is left exactly as it was. The new line uses the page’s own serif font, so it matches the text around it.
</details>

## Troubleshooting

<details>
<summary><strong>Windows SmartScreen won’t let me open the app</strong></summary>

<br>

The app isn’t code-signed, so SmartScreen warns the first time. Choose **More info → Run anyway**.
</details>

<details>
<summary><strong>“Couldn’t save name-clean.pdf. If it’s open in a PDF viewer, close it and try again.”</strong></summary>

<br>

A cleaned copy from an earlier run is still open in a PDF viewer, and Windows won’t let it be replaced. Close it and press **Remove Watermarks** again.
</details>

<details>
<summary><strong>“Nothing to remove”</strong></summary>

<br>

No SenAI title or footer was found in that file, and nothing needed fixing. It may already be clean, or it may not come from SenAI. An unchanged copy is still saved, so you always get a `-clean.pdf`.
</details>

<details>
<summary><strong>“This PDF is password protected, so it can’t be cleaned.”</strong></summary>

<br>

Password-protected PDFs can’t be opened for cleaning.
</details>

<details>
<summary><strong>“This file isn’t a readable PDF.”</strong></summary>

<br>

The file is damaged, incomplete, or not actually a PDF. Try downloading it again.
</details>

<details>
<summary><strong>Are my files uploaded anywhere?</strong></summary>

<br>

No. Everything happens on your computer, and nothing is sent over the internet.
</details>

## Command line

The command line needs only Python 3.9+ and [pypdf](https://pypi.org/project/pypdf/), not Qt:

```bash
pip install .

senai-remover homework.pdf                 # -> homework-clean.pdf
senai-remover ~/Downloads/senai            # every PDF in a folder
senai-remover *.pdf -o cleaned/            # into another folder, keeping the same names
senai-remover homework.pdf --in-place      # overwrite the original
senai-remover homework.pdf --name "Brinn - {name}"    # -> Brinn - homework.pdf
senai-remover homework.pdf --title "Week 7 answers"   # a different title ("" for none)
senai-remover homework.pdf --no-repair     # leave SenAI's typesetting as it is
senai-remover --version
```

If SenAI ever adds other branding, `--pattern` removes extra text. It takes a case-insensitive regular expression and can be repeated:

```bash
senai-remover homework.pdf --pattern "made with senai"
```

To run the app itself from source:

```bash
pip install ".[gui]"
senai-remover-gui                          # or: python -m senai_remover
```

`python -m senai_remover` with no arguments, or with `--design N`, opens the app. With any other arguments it behaves like `senai-remover`.

## How it works

SenAI PDFs are made by headless Chrome (Skia), and the branding is ordinary text, so it can be removed exactly:

```mermaid
flowchart LR
    A[PDF page] --> B[Each text object<br/>BT … ET]
    B --> C[Decode glyphs to Unicode<br/>via the font's ToUnicode map]
    C --> D{Matches senai.uk<br/>or SenAI Maths?}
    D -- no --> E[Leave it alone]
    D -- yes --> F{Would deleting it move<br/>other text on that line?}
    F -- no --> G[Delete the text-drawing<br/>operators for those glyphs]
    F -- yes --> H[Hide that run instead<br/>text render mode 3]
    G --> T[Draw the new title where<br/>SenAI Maths started]
    H --> T
    E --> R
    T --> R[Repair the typesetting]
    R --> I[Also remove senai.uk links<br/>and matching metadata]
    I --> J[Save name-clean.pdf]
```

Only the text-drawing operators (`Tj`, `TJ`, `'` and `"`) that draw the branding are removed. Every other operator on the page is kept.

Then the typesetting repairs. SenAI sets maths with the Liberation fonts, which lack some symbols, so Chrome drew glyph 0 (an empty box) instead. Every glyph on the page is located, with its font, size and position. A box is worked out from its surroundings: a small raised one after a number is a degree sign, one spaced like a binary operator is a dot, and one spaced like a relation is the implies arrow. Chrome’s own ActualText hint is used when it left one. The box is taken out without moving anything else on the line, and the symbol is drawn in its place in the same font family, from another font in the file, or from a standard PDF font. Sentences that lost their spaces are split back into words and set again in the page’s upright serif.

## Accessibility

- Every theme follows Windows’ light or dark mode, or the Appearance you choose in Settings.
- Every text colour pair each theme declares is tested at **4.5:1 contrast or better**, in light, dark and high contrast.
- The themes respect Windows’ high-contrast, transparency and animation settings.
- Everything works from the keyboard, focus is always visible, and icon-only buttons have names for screen readers.

## Building from source

<details>
<summary><strong>Development setup, tests and tools</strong></summary>

<br>

```bash
pip install -e ".[gui,test]"
QT_QPA_PLATFORM=offscreen pytest           # no display needed
python tools/screenshots.py shots/         # renders every theme, light and dark
python tools/make_icon.py                  # redraws the app icon (needs Pillow)
```

The tests cover the PDF cleaner, the typesetting repairs, the command line and the app’s file model. They also drive every theme offscreen, covering:

- adding files and drag and drop
- cleaning and keyboard shortcuts
- switching themes
- contrast checks

`tests/fixtures/senai_sample.pdf` is a stand-in for a real SenAI export, and `tests/fixtures/maths_sample.pdf` reproduces SenAI’s typesetting faults: Chrome printing MathML with only the Liberation fonts. `make_sample.cjs` and `make_maths_sample.cjs`, next to them, make both with the same Chrome/Skia pipeline (they need Node and Playwright).
</details>

<details>
<summary><strong>Building the Windows .exe</strong></summary>

<br>

```bash
pip install ".[gui]" pyinstaller
python tools/make_version_info.py build/version_info.txt
pyinstaller --onefile --windowed --name SenAI-Watermark-Remover \
  --version-file build/version_info.txt \
  --icon senai_remover/gui/assets/app.ico \
  --add-data "senai_remover/gui/assets:senai_remover/gui/assets" \
  --paths . senai_remover/__main__.py
```

The app ends up in `dist/SenAI-Watermark-Remover.exe`.
</details>

<details>
<summary><strong>Working on it with Claude Code</strong></summary>

<br>

The repository is set up as a Claude Code project:

- [`CLAUDE.md`](CLAUDE.md) describes the architecture, commands, theme rules, release steps and known issues, so every session starts with full context.
- A SessionStart hook ([`.claude/hooks/session-start.sh`](.claude/hooks/session-start.sh)) installs the dependencies and Qt's libraries in cloud sessions, so tests run straight away.
- Project skills (slash commands):
  - `/build-exe` builds and smoke-tests the Windows app under Wine.
  - `/release` cuts a version.
  - `/screenshots` regenerates the images.
  - `apple-design` reviews UI against Apple's Human Interface Guidelines.
</details>

<details>
<summary><strong>Project layout</strong></summary>

<br>

```text
senai_remover/
├── core.py              PDF cleaning, the new title, output names
├── repair.py            fixing SenAI's missing symbols and spaces
├── pdftext.py           finding every glyph on a page; removing and drawing text
├── _words.py            English word list (generated by tools/make_words.py)
├── _metrics.py          standard PDF font widths (generated by tools/make_metrics.py)
├── cli.py               command line
└── gui/
    ├── app.py           start-up and theme switching
    ├── controller.py    file list model and background cleaning
    ├── model.py         file statuses, output names, messages (no Qt)
    ├── settings.py      saved theme, appearance, title and output name
    ├── settings_panel.py
    ├── theme.py         fonts, icons, colour maths, system settings
    ├── widgets.py       shared widgets
    ├── designs/         base.py plus one file per theme
    └── assets/          fonts, icons, theme previews, app icon
tests/                   pytest suite and the sample PDFs
tools/                   screenshots, icon, .exe details, word list and font width generators
docs/screenshots/        README images
.github/workflows/       ci.yml and release.yml
CLAUDE.md, .claude/      Claude Code project: context, settings, hook, skills
```
</details>

## Code signing policy

Releases aren't code-signed yet. When they are, this policy applies:

- Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).
- Only `SenAI-Watermark-Remover.exe` is signed, and only when the [Release workflow](.github/workflows/release.yml) has built it on GitHub from this repository's source. Nothing built anywhere else is signed.
- Every release is approved by hand before it's signed.
- Team roles: [Brinn (ImBrinn)](https://github.com/ImBrinn) is the committer, reviewer and approver. Changes from anyone else are reviewed before they're merged.
- Privacy: this program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it. It never connects to the internet; your PDFs stay on your computer.

## Credits and licences

SenAI Watermark Remover is free and open source under the [MIT licence](LICENSE). It uses:

- [Qt 6.8](https://www.qt.io/) via [PySide6](https://pypi.org/project/PySide6-Essentials/) (LGPL)
- [Inter](https://rsms.me/inter/) typeface (SIL Open Font License)
- [Lucide](https://lucide.dev/) icons (ISC licence)
- [pypdf](https://pypi.org/project/pypdf/) (BSD)
- The English word list from [wordninja](https://github.com/keredson/wordninja) (MIT), and standard PDF font widths from Adobe’s Core 14 AFM files

The licence texts for Inter and Lucide are included in [`senai_remover/gui/assets/`](senai_remover/gui/assets/).

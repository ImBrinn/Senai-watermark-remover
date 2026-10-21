# SenAI Watermark Remover

Removes the SenAI branding from SenAI Maths PDFs:

- the **"SenAI Maths"** title at the top of page 1
- the **senai.uk** footer on every page

Everything else (answers, working, diagrams, page numbers) is left exactly as
it was. The branding text is deleted from the PDF itself rather than covered
with a white box.

## Windows app

Every push to `main` builds a single-file Windows app: open the
[Actions tab](../../actions), pick the latest **CI** run, and download
**SenAI-Watermark-Remover-windows**. Pushing a tag such as `v2.0.0` also
attaches the `.exe` to a GitHub release.

Double-click `SenAI-Watermark-Remover.exe`, then drag PDFs (or a folder) onto
the window, or click **Add Files…**. Click **Remove Watermarks** or press
Ctrl+Enter. Cleaned copies are saved as `name_clean.pdf` next to the originals,
or in a folder you choose; originals are never changed.

Windows may show a SmartScreen warning the first time because the app isn't
code-signed; choose **More info → Run anyway**.

### Four design prototypes

The app ships four interchangeable designs. Switch with **Ctrl+1** to **Ctrl+4**
(also in the View menu or the ⋯ menu); the file list carries over.

| | Design | Idea |
|---|---|---|
| 1 | Apple Classic | Mac-style window following Apple's Human Interface Guidelines: menu bar, symbol toolbar, inset list, status bar |
| 2 | Apple Liquid Glass | Apple's current look: glass toolbar capsules over content that scrolls beneath them |
| 3 | Exercise Book | Squared maths paper, a red margin, highlighter selection and teacher-style ticks; a chalkboard in dark mode |
| 4 | Windows 11 Fluent | Native Windows 11 styling: command bar, cards, InfoBar messages |

Every design follows the system's light or dark mode, keeps text contrast at
4.5:1 or better, and responds to Windows' high contrast, transparency and
animation settings. Start on a particular design with `--design 3`.

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| Ctrl+O | Add files |
| Ctrl+Shift+O | Add a folder |
| Ctrl+Enter | Remove watermarks |
| Delete | Remove the selected files from the list |
| Ctrl+1 … Ctrl+4 | Switch design |

## Running from source

Needs Python 3.9 or newer.

```bash
pip install ".[gui]"
senai-remover-gui                         # open the app
senai-remover homework.pdf                # -> homework_clean.pdf
senai-remover ~/Downloads/senai           # every PDF in a folder
senai-remover *.pdf -o cleaned/           # save into another folder, same names
senai-remover homework.pdf --in-place     # overwrite the original
```

The command line only needs `pip install .` (no Qt). `python -m senai_remover`
with no arguments opens the app; with arguments it behaves like
`senai-remover`.

If SenAI ever adds other branding text, `--pattern` removes extra text
(a case-insensitive regular expression), e.g.
`senai-remover hw.pdf --pattern "made with senai"`.

## How it works

SenAI PDFs are rendered by headless Chrome, and the branding is ordinary
text. For each text object on each page the tool decodes the glyphs back to
Unicode using the font's ToUnicode map, looks for `senai.uk` and
`SenAI Maths`, and deletes just the drawing commands for those glyphs.
Links to senai.uk and document metadata that mention SenAI are removed too.

## Development

```bash
pip install -e ".[gui,test]"
pytest
python tools/screenshots.py shots/        # every design, light and dark, three states
python tools/make_icon.py                 # redraws the app icon (needs Pillow)
```

`tests/fixtures/senai_sample.pdf` is a stand-in for a real SenAI export,
made with the same Chrome/Skia pipeline by `tests/fixtures/make_sample.cjs`
(requires Node and Playwright).

The app uses Qt 6.8 (PySide6), the Inter typeface (SIL Open Font License)
and Lucide icons (ISC License); their licences are next to the files in
`senai_remover/gui/assets/`.

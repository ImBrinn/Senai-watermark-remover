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
**SenAI-Watermark-Remover-windows**. Pushing a tag such as `v1.0.0` also
attaches the `.exe` to a GitHub release.

Double-click `SenAI-Watermark-Remover.exe`, click **Add PDFs…** (or
**Add folder…**), then **Remove watermark**. Cleaned copies are saved next
to the originals as `name_clean.pdf`, or in a folder you choose. You can
also drag PDFs onto the `.exe` to open the app with them already listed.

Windows may show a SmartScreen warning the first time because the app isn't
code-signed; choose **More info → Run anyway**.

## Running from source

Needs Python 3.9 or newer.

```bash
pip install .
senai-remover-gui                         # open the app
senai-remover homework.pdf                # -> homework_clean.pdf
senai-remover ~/Downloads/senai           # every PDF in a folder
senai-remover *.pdf -o cleaned/           # save into another folder, same names
senai-remover homework.pdf --in-place     # overwrite the original
```

Without installing: `pip install pypdf`, then `python -m senai_remover`
(no arguments opens the app, otherwise it takes the same options as
`senai-remover`).

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
pip install -e ".[test]"
pytest
```

`tests/fixtures/senai_sample.pdf` is a stand-in for a real SenAI export,
made with the same Chrome/Skia pipeline by `tests/fixtures/make_sample.cjs`
(requires Node and Playwright).

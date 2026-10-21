---
name: build-exe
description: Build SenAI-Watermark-Remover.exe with real Windows Python under Wine in a Linux cloud session, run the test suite on Windows Python, and smoke-test the exe (add PDFs, clean, switch themes) with screenshots. Use when asked for a Windows build, an .exe to hand over, or to check the app on Windows.
---

# Build and smoke-test the Windows .exe under Wine

PyInstaller can't cross-compile, so build with Windows Python running in Wine.
Keep everything in the scratchpad (`$S` below). Expect about 10 minutes the
first time and about 2 minutes after that.

## One-time setup

```bash
S=<scratchpad>/win; mkdir -p $S/msi; export WINEPREFIX=$S/prefix WINEARCH=win64 WINEDEBUG=-all
apt-get install -y -qq wine64 xvfb xdotool imagemagick
# python.org's installer .exe is a 32-bit bootstrapper and fails on 64-bit-only
# Wine, so install the 64-bit MSIs directly instead:
for m in core exe lib tcltk; do curl -sSfL -o $S/msi/$m.msi https://www.python.org/ftp/python/3.12.10/amd64/$m.msi; done
for m in core exe lib tcltk; do wine msiexec /i $S/msi/$m.msi /qn TARGETDIR='C:\Python312' ALLUSERS=0; done
export PIP_CERT='Z:\root\.ccr\ca-bundle.crt'    # the cloud proxy's CA
W() { wine 'C:\Python312\python.exe' "$@" < /dev/null 2>&1 | cat; }
W -m ensurepip
W -m pip install -q "PySide6-Essentials==6.8.3" "shiboken6==6.8.3" pypdf pyinstaller pytest
```

**Always run Windows programs as `... < /dev/null 2>&1 | cat`.** If you send
Wine's output straight to a file, or close stdin, Python fails with
`init_sys_streams: Invalid handle`, or the exe shows "Failed to start embedded
python interpreter". Both are Wine artefacts, not app bugs.

## Build

```bash
rm -rf $S/src && mkdir -p $S/src && tar --exclude=.git --exclude=__pycache__ -cf - . | tar -xf - -C $S/src
cd $S/src
QT_QPA_PLATFORM=offscreen W -m pytest -q        # the whole suite on Windows Python
W -m PyInstaller --noconfirm --onefile --windowed --name SenAI-Watermark-Remover \
  --icon senai_remover/gui/assets/app.ico --add-data "senai_remover/gui/assets:senai_remover/gui/assets" \
  --paths . senai_remover/__main__.py | grep -E "ERROR|Build complete"
sha256sum dist/SenAI-Watermark-Remover.exe       # about 38 MB
```

## Smoke test

1. Start `Xvfb :88 -screen 0 1280x900x24` as a background task. It has to
   survive between commands.
2. Start the exe as another background task. Pass the files as `Z:\...` paths:
   `wine $S/src/dist/SenAI-Watermark-Remover.exe --design 3 "Z:\path\a.pdf" < /dev/null 2>&1 | cat`.
3. Drive it with `DISPLAY=:88`:
   - `xdotool search --name '^SenAI Watermark Remover$'`, then `windowactivate`
   - `xdotool key ctrl+Return` to clean
   - `ctrl+1`…`ctrl+4` to switch theme and `ctrl+comma` to open Settings
   - after each step, `import -window root shot.png`, then Read the PNG
4. Check that `*_clean.pdf` files appeared, and that the rows and summary read
   "Cleaned".
5. Stop everything with `WINEPREFIX=$S/prefix wineserver -k`. Never use
   `pkill -f SenAI...`, because it matches and kills your own shell.

There's no window manager, so screenshots show no title bar. That's expected.
Segoe UI isn't in Wine either, so the Fluent theme falls back to Inter.

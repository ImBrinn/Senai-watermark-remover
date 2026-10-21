"""Entry point for ``python -m senai_remover`` and the standalone executable.

With no arguments (or when there is no console, e.g. PDFs dropped onto the
.exe) the GUI opens; otherwise the command line interface runs.
"""

import sys

if __name__ == "__main__":
    # Absolute imports so this file also works as a PyInstaller entry script.
    args = sys.argv[1:]
    if not args or sys.stdout is None:
        from senai_remover import gui

        sys.exit(gui.main(args))
    from senai_remover import cli

    sys.exit(cli.main(args))

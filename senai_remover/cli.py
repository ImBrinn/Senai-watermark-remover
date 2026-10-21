"""Command line interface: ``senai-remover homework.pdf [more.pdf | folder ...]``."""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Iterator, Optional, Sequence

from . import __version__
from .core import DEFAULT_PATTERNS, CleanResult, clean_pdf, default_output_path


def find_pdfs(paths: Iterable[Path], skip_suffix: str = "") -> Iterator[Path]:
    """Expand folders into the PDFs directly inside them.

    Files whose name already ends in ``skip_suffix`` (earlier output) are
    skipped when scanning a folder, but not when named explicitly.
    """
    for path in paths:
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if child.is_file() and child.suffix.lower() == ".pdf":
                    if not (skip_suffix and child.stem.endswith(skip_suffix)):
                        yield child
        else:
            yield path


def describe(result: CleanResult) -> str:
    """One-line summary of what was removed, e.g. "SenAI Maths, senai.uk x8"."""
    counts = Counter(text for _, text in result.removed)
    return ", ".join(t if n == 1 else f"{t} x{n}" for t, n in counts.items())


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="senai-remover",
        description="Remove the SenAI branding (title and senai.uk footer) from PDFs.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="PDF files or folders of PDFs")
    out = parser.add_mutually_exclusive_group()
    out.add_argument("-o", "--output-dir", type=Path,
                     help="save cleaned PDFs here, keeping their names (default: next to the original)")
    out.add_argument("--in-place", action="store_true", help="overwrite the original files")
    parser.add_argument("--suffix", help='added to output file names (default: "_clean", or "" with -o)')
    parser.add_argument("--pattern", action="append", default=[], metavar="REGEX",
                        help="extra text to remove (case-insensitive regex); may be repeated")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    # pypdf logs harmless warnings about the generator's slightly-off xref tables.
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    patterns = [*DEFAULT_PATTERNS, *args.pattern]
    suffix = args.suffix if args.suffix is not None else ("" if args.output_dir else "_clean")

    failures = cleaned = total = 0
    for source in find_pdfs(args.paths, skip_suffix=suffix):
        total += 1
        target = source if args.in_place else default_output_path(source, args.output_dir, suffix)
        if not args.in_place and target.resolve() == source.resolve():
            print(f"FAIL {source}: output would overwrite the original (use --in-place)", file=sys.stderr)
            failures += 1
            continue
        try:
            result = clean_pdf(source, target, patterns)
        except Exception as exc:  # report and carry on with the other files
            print(f"FAIL {source}: {exc}", file=sys.stderr)
            failures += 1
            continue
        for warning in result.warnings:
            print(f"WARN {source.name}: {warning}", file=sys.stderr)
        if result.changed:
            cleaned += 1
            print(f"OK   {source} -> {target}  (removed: {describe(result)})")
        else:
            print(f"--   {source} -> {target}  (no SenAI branding found)")

    if total == 0:
        print("No PDF files found.", file=sys.stderr)
        return 1
    print(f"Cleaned {cleaned} of {total} file(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

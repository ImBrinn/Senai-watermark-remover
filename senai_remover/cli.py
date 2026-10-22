"""Command line interface: ``senai-remover homework.pdf [more.pdf | folder ...]``."""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Iterator, Optional, Sequence

from . import __version__
from .core import (
    DEFAULT_NAME,
    DEFAULT_PATTERNS,
    DEFAULT_TITLE,
    CleanResult,
    clean_pdf,
    default_output_path,
    is_output_name,
    name_problem,
)


def find_pdfs(paths: Iterable[Path], template: str = DEFAULT_NAME) -> Iterator[Path]:
    """Expand folders into the PDFs directly inside them.

    Files that look like earlier cleaned copies (named by ``template``) are
    skipped when scanning a folder, but not when named explicitly.
    """
    for path in paths:
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if child.is_file() and child.suffix.lower() == ".pdf":
                    if not is_output_name(child.stem, template):
                        yield child
        else:
            yield path


# How each kind of repair is described: (one, more than one).
FIXES = {
    "°": ("degree sign", "degree signs"),
    "·": ("multiplication dot", "multiplication dots"),
    "⟹": ("arrow", "arrows"),
    "⇒": ("arrow", "arrows"),
    "spaces": ("sentence respaced", "sentences respaced"),
}


def describe(result: CleanResult) -> str:
    """One-line summary, e.g. "removed SenAI Maths, senai.uk x8; fixed 43 degree signs"."""
    parts = []
    removed = Counter(text for _, text in result.removed)
    if removed:
        parts.append("removed " + ", ".join(t if n == 1 else f"{t} x{n}" for t, n in removed.items()))
    if result.title:
        parts.append(f"title: {result.title}")
    fixed = Counter(FIXES.get(what, ("symbol", "symbols")) for _, what in result.repaired)
    order = list(dict.fromkeys([*FIXES.values(), ("symbol", "symbols")]))
    if fixed:
        parts.append("fixed " + ", ".join(f"{fixed[k]} {k[0] if fixed[k] == 1 else k[1]}"
                                          for k in order if fixed[k]))
    return "; ".join(parts)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="senai-remover",
        description="Remove the SenAI branding from PDFs, put your own title in its place, "
                    "and fix SenAI's typesetting.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="PDF files or folders of PDFs")
    out = parser.add_mutually_exclusive_group()
    out.add_argument("-o", "--output-dir", type=Path,
                     help="save cleaned PDFs here, keeping their names (default: next to the original)")
    out.add_argument("--in-place", action="store_true", help="overwrite the original files")
    naming = parser.add_mutually_exclusive_group()
    naming.add_argument("--name", metavar="TEMPLATE",
                        help='name for cleaned copies, with {name} for the original name '
                             f'(default: "{DEFAULT_NAME}", or "{{name}}" with -o)')
    naming.add_argument("--suffix", help="added after the original name instead (--suffix _clean)")
    parser.add_argument("--title", default=DEFAULT_TITLE,
                        help=f'title to put where SenAI\'s was (default: "{DEFAULT_TITLE}"; "" for none)')
    parser.add_argument("--no-repair", action="store_true",
                        help="don't fix SenAI's typesetting (empty boxes, missing spaces)")
    parser.add_argument("--pattern", action="append", default=[], metavar="REGEX",
                        help="extra text to remove (case-insensitive regex); may be repeated")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)
    _replace_unprintable()

    # pypdf logs harmless warnings about the generator's slightly-off xref tables.
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    patterns = [*DEFAULT_PATTERNS, *args.pattern]
    if args.name is not None:
        template = args.name
    elif args.suffix is not None:
        template = "{name}" + args.suffix
    else:
        template = "{name}" if args.output_dir else DEFAULT_NAME
    problem = name_problem(template)
    if problem:
        parser.error(f"--name {template!r}: {problem}")

    failures = cleaned = total = 0
    for source in find_pdfs(args.paths, template):
        total += 1
        target = source if args.in_place else default_output_path(source, args.output_dir, template=template)
        if not args.in_place and target.resolve() == source.resolve():
            print(f"FAIL {source}: output would overwrite the original (use --in-place)", file=sys.stderr)
            failures += 1
            continue
        try:
            result = clean_pdf(source, target, patterns, title=args.title, repair=not args.no_repair)
        except Exception as exc:  # report and carry on with the other files
            print(f"FAIL {source}: {exc}", file=sys.stderr)
            failures += 1
            continue
        for warning in result.warnings:
            print(f"WARN {source.name}: {warning}", file=sys.stderr)
        if result.changed or result.repaired:
            cleaned += 1
            print(f"OK   {source} -> {target}  ({describe(result)})")
        else:
            print(f"--   {source} -> {target}  (no SenAI branding found)")

    if total == 0:
        print("No PDF files found.", file=sys.stderr)
        return 1
    print(f"Cleaned {cleaned} of {total} file(s).")
    return 1 if failures else 0


def _replace_unprintable() -> None:
    """Print characters the console can't show as "?" instead of crashing.

    Windows consoles and pipes often use Windows-1252, which has no "⟹" and
    no characters from other alphabets, which file names can contain.
    """
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except (ValueError, OSError):
                pass


if __name__ == "__main__":
    sys.exit(main())

"""Command line interface: ``senai-remover homework.pdf [more.pdf | folder ...]``."""

from __future__ import annotations

import argparse
import json
import logging
import stat
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
    report_payload,
    report_text,
    safe_error,
    same_file,
    scan_pdf,
    title_problem,
)


def find_pdfs(paths: Iterable[Path], template: str = DEFAULT_NAME) -> Iterator[Path]:
    """Expand folders into the PDFs directly inside them.

    Files that look like earlier cleaned copies (named by ``template``) are
    skipped when scanning a folder, but not when named explicitly.

    A folder reached through a symlink is not opened, and a symlink inside a
    folder is not followed. Only a regular file (not a device or a socket)
    is yielded from a folder. A symlink named on its own is still yielded
    when it points at a file, so a path someone typed is not silently dropped.
    """
    for path in paths:
        if path.is_symlink() and path.is_dir():
            continue
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if child.is_symlink() or not child.is_file():
                    continue
                info = child.lstat()
                if not stat.S_ISREG(info.st_mode):
                    continue
                if child.suffix.lower() == ".pdf" and not is_output_name(child.stem, template):
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
    """One-line summary, e.g. "removed SenAI Maths, senai.uk x8; fixed 43 degree signs".

    Link addresses and metadata values are left out: a matched footer is
    branding, but a document title can carry someone's work.
    """
    parts = []
    removed = Counter(result.branding_texts())
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


def format_report(results: Sequence[CleanResult], kind: str) -> str:
    """``text`` or ``json``. Several files become a JSON list; one stays an object."""
    if kind == "json":
        payload = [report_payload(result) for result in results]
        body = payload[0] if len(payload) == 1 else payload
        return json.dumps(body, indent=2) + "\n"
    return "\n\n".join(report_text(result) for result in results) + ("\n" if results else "")


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
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would change, without writing a file")
    parser.add_argument("--report", choices=("text", "json"),
                        help="print a change report of kinds and counts (text or json)")
    parser.add_argument("--report-file", type=Path, metavar="PATH",
                        help="write that report to this file as well")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)
    _replace_unprintable()

    # pypdf's own messages sometimes quote bytes from the file. Silence them
    # so a log never carries text from a page.
    logging.getLogger("pypdf").disabled = True
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
    problem = title_problem(args.title)
    if problem:
        parser.error(f"--title {args.title!r}: {problem}")

    failures = cleaned = total = 0
    reports: list[CleanResult] = []
    for source in find_pdfs(args.paths, template):
        total += 1
        try:
            if args.dry_run:
                result = scan_pdf(source, patterns, title=args.title, repair=not args.no_repair)
            else:
                target = source if args.in_place else default_output_path(
                    source, args.output_dir, template=template)
                if not args.in_place and same_file(target, source):
                    print(f"FAIL {source}: output would overwrite the original (use --in-place)",
                          file=sys.stderr)
                    failures += 1
                    continue
                result = clean_pdf(source, target, patterns, title=args.title,
                                   repair=not args.no_repair, overwrite=args.in_place)
        except RecursionError:
            # On its own, ahead of Exception, so a nested file can't take the
            # batch down — and its message is not printed.
            print(f"FAIL {source}: This PDF is too deeply nested to open.", file=sys.stderr)
            failures += 1
            continue
        except Exception as exc:  # report and carry on with the other files
            print(f"FAIL {source}: {safe_error(exc)}", file=sys.stderr)
            failures += 1
            continue
        reports.append(result)
        for warning in result.warnings:
            print(f"WARN {source.name}: {warning}", file=sys.stderr)
        if args.report:
            if result.changed or result.repaired:
                cleaned += 1
            continue
        if result.changed or result.repaired:
            cleaned += 1
            if args.dry_run:
                print(f"OK   {source}  (dry run: {describe(result)})")
            else:
                print(f"OK   {source} -> {result.output}  ({describe(result)})")
        elif args.dry_run:
            print(f"--   {source}  (dry run: no SenAI branding found)")
        else:
            print(f"--   {source} -> {result.output}  (no SenAI branding found)")

    if args.report or args.report_file:
        kind = args.report or ("json" if args.report_file.suffix.lower() == ".json" else "text")
        text = format_report(reports, kind)
        if args.report:
            sys.stdout.write(text)
        if args.report_file is not None:
            args.report_file.parent.mkdir(parents=True, exist_ok=True)
            args.report_file.write_text(text, encoding="utf-8")

    if total == 0:
        print("No PDF files found.", file=sys.stderr)
        return 1
    summary = f"{'Checked' if args.dry_run else 'Cleaned'} {cleaned} of {total} file(s)."
    # A JSON report has to be the whole of stdout, so the summary goes beside it.
    print(summary, file=sys.stderr if args.report == "json" else sys.stdout)
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

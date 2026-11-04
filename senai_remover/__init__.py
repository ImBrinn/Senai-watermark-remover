"""Remove the SenAI branding from PDFs, put your own title in its place, and fix SenAI's typesetting."""

from .core import DEFAULT_PATTERNS, Change, CleanResult, clean_pdf, default_output_path, scan_pdf

__version__ = "2.4.0"
__all__ = ["DEFAULT_PATTERNS", "Change", "CleanResult", "clean_pdf", "default_output_path",
           "scan_pdf", "__version__"]

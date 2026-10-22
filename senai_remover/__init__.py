"""Remove the SenAI branding from PDFs, put your own title in its place, and fix SenAI's typesetting."""

from .core import DEFAULT_PATTERNS, CleanResult, clean_pdf, default_output_path

__version__ = "2.1.2"
__all__ = ["DEFAULT_PATTERNS", "CleanResult", "clean_pdf", "default_output_path", "__version__"]

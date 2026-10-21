"""Remove the SenAI branding (title and senai.uk footer) from PDFs."""

from .core import DEFAULT_PATTERNS, CleanResult, clean_pdf, default_output_path

__version__ = "2.1.0"
__all__ = ["DEFAULT_PATTERNS", "CleanResult", "clean_pdf", "default_output_path", "__version__"]

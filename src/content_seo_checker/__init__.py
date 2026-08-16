"""Pre-publish SEO and structured-data validation."""

from .config import CheckerConfig
from .models import Document, Finding, ScanReport, Severity
from .scanner import scan_path, scan_text

__all__ = [
    "CheckerConfig",
    "Document",
    "Finding",
    "ScanReport",
    "Severity",
    "scan_path",
    "scan_text",
]

__version__ = "0.2.0"

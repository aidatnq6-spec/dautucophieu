"""Text per page from a PDF (pypdf). Image-only or unreadable files give no pages; no OCR."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_pages(data: bytes, *, max_pages: int = 60) -> list[str]:
    try:
        reader = PdfReader(BytesIO(data))
        return [(page.extract_text() or "") for page in reader.pages[:max_pages]]
    except (PdfReadError, ValueError, KeyError, TypeError):
        return []

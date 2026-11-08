"""Text of scanned PDF pages, read on this machine: each page without a usable text layer is drawn as a greyscale image at
300 dpi (pypdfium2) and piped to Tesseract with its Vietnamese model ("vie"). Nothing is sent anywhere and nothing is written
to disk. OCR misreads digits now and then, so whatever is read this way stays a proposal the owner checks against the file."""

import os
import re
import shutil
import subprocess
import time
import unicodedata
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from functools import lru_cache
from pathlib import Path
from typing import Callable

DPI = 300
MAX_OCR_PAGES = 120
MAX_OCR_SECONDS = 240
_VIETNAMESE = re.compile("[ăâđêôơưàáạảãầấậẩẫằắặẳẵèéẹẻẽềếệểễìíịỉĩòóọỏõồốộổỗờớợởỡùúụủũừứựửữỳýỵỷỹ]", re.I)
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # no console window flashing per page
_DEFAULT_EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")

Reader = Callable[[bytes], str]


def needs_ocr(text: str) -> bool:
    """A Vietnamese report page has accented letters on every line; a scan has none, or a broken font layer without them."""
    return len(_VIETNAMESE.findall(unicodedata.normalize("NFC", text))) < 20


@lru_cache(maxsize=1)
def find_tesseract() -> str | None:
    """Tesseract with the Vietnamese model, from TESSERACT_EXE, the PATH or its usual install folder; None when absent."""
    for candidate in (os.environ.get("TESSERACT_EXE"), shutil.which("tesseract"), str(_DEFAULT_EXE)):
        if not candidate or not Path(candidate).is_file():
            continue
        try:
            langs = subprocess.run([candidate, "--list-langs"], capture_output=True, timeout=20, creationflags=_NO_WINDOW)
        except (OSError, subprocess.SubprocessError):
            continue
        if re.search(rb"^vie\s*$", langs.stdout, re.M):
            return candidate
    return None



def tesseract_reader(exe: str) -> Reader:
    def read(image: bytes) -> str:
        # --psm 6: one uniform block, which keeps a table row's label and its amounts on one line.
        done = subprocess.run([exe, "stdin", "stdout", "-l", "vie", "--psm", "6"], input=image, capture_output=True, timeout=120,
                              creationflags=_NO_WINDOW)
        return done.stdout.decode("utf-8", "replace") if done.returncode == 0 else ""
    return read


def default_reader() -> Reader | None:
    exe = find_tesseract()
    return tesseract_reader(exe) if exe else None


def _pgm(page) -> bytes:
    bitmap = page.render(scale=DPI / 72, grayscale=True)
    w, h, stride, raw = bitmap.width, bitmap.height, bitmap.stride, bytes(bitmap.buffer)
    rows = raw if stride == w else b"".join(raw[y * stride:y * stride + w] for y in range(h))
    return b"P5 %d %d 255\n" % (w, h) + rows


def with_ocr(data: bytes, pages: list[str], *, read: Reader | None, max_pages: int = MAX_OCR_PAGES,
             max_seconds: float = MAX_OCR_SECONDS) -> tuple[list[str], frozenset[int], list[str]]:
    """The pages with each image page's text replaced by OCR; the 0-based pages read that way; notes for the owner."""
    wanted = [i for i, text in enumerate(pages) if needs_ocr(text)]
    if not wanted:
        return pages, frozenset(), []
    if read is None:
        return pages, frozenset(), [f"Có {len(wanted)} trang dạng ảnh nhưng máy chưa cài Tesseract kèm dữ liệu tiếng Việt (vie), nên không "
                                    "nhận dạng được chữ trên các trang đó; hãy nhập tay hoặc cài Tesseract."]
    notes = []
    if len(wanted) > max_pages:
        notes.append(f"Chỉ nhận dạng chữ {max_pages}/{len(wanted)} trang dạng ảnh đầu tiên.")
        wanted = wanted[:max_pages]
    try:
        import pypdfium2 as pdfium
        document = pdfium.PdfDocument(data)
    except Exception:
        return pages, frozenset(), ["Không vẽ được trang PDF thành ảnh để nhận dạng chữ; hãy nhập tay."]
    out, read_ok, deadline = list(pages), set(), time.monotonic() + max_seconds
    try:
        # Drawing stays on this thread (PDFium is not thread-safe); Tesseract runs as separate processes, several at a time.
        with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as pool:
            running = {}
            for i in wanted:
                if time.monotonic() > deadline:
                    break
                running[pool.submit(read, _pgm(document[i]))] = i
            pending = set(running)
            while pending and (left := deadline - time.monotonic()) > 0:
                done, pending = wait(pending, timeout=left, return_when=FIRST_COMPLETED)
                for future in done:
                    text = future.result() if future.exception() is None else ""
                    if text.strip():
                        out[running[future]] = text
                        read_ok.add(running[future])
            for future in pending:
                future.cancel()
    finally:
        document.close()
    if len(read_ok) < len(wanted):
        notes.append(f"Nhận dạng được chữ {len(read_ok)}/{len(wanted)} trang dạng ảnh (hết thời gian hoặc trang không có chữ).")
    return out, frozenset(read_ok), notes

"""Upload validation and text extraction for PDF, DOCX and TXT."""
import hashlib
import io
from dataclasses import dataclass, field
from pathlib import Path

from config.constants import SUPPORTED_EXTENSIONS

LINES_PER_PAGE = 55  # screenplay convention, used only when real pages are unavailable


class DocumentError(Exception):
    """User-presentable extraction/validation failure."""


@dataclass
class LoadedDocument:
    filename: str
    file_type: str
    sha256: str
    size_bytes: int
    pages: list
    warnings: list = field(default_factory=list)
    page_basis: str = "actual"  # "actual" or "estimated"

    @property
    def text(self) -> str:
        return "\n\n".join(self.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)


def validate_upload(filename: str, size: int, max_mb: int) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise DocumentError(f"Unsupported file type '{ext or 'unknown'}'. Upload PDF, DOCX or TXT.")
    if size == 0:
        raise DocumentError("The file is empty.")
    if size > max_mb * 1024 * 1024:
        raise DocumentError(f"File is {size / 1048576:.1f} MB; the limit is {max_mb} MB.")
    return ext


def _paginate(text: str) -> list:
    if "\f" in text:
        pages = [p for p in text.split("\f")]
        return [p for p in pages if p.strip()] or [text]
    lines = text.splitlines()
    return ["\n".join(lines[i:i + LINES_PER_PAGE]) for i in range(0, len(lines), LINES_PER_PAGE)] or [text]


def _decode(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise DocumentError("Could not decode the text file.")


def _load_pdf(data: bytes, warnings: list) -> list:
    pages = None
    try:
        import fitz  # PyMuPDF
        with fitz.open(stream=data, filetype="pdf") as doc:
            if doc.needs_pass:
                raise DocumentError("The PDF is password protected.")
            pages = [p.get_text("text") for p in doc]
    except ImportError:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise DocumentError("The PDF is password protected.")
            pages = [(p.extract_text() or "") for p in reader.pages]
            warnings.append("PyMuPDF not installed; used the pypdf fallback (layout may be less accurate).")
        except ImportError:
            raise DocumentError("No PDF library available. Install PyMuPDF: pip install pymupdf")
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError(f"Could not read the PDF ({exc.__class__.__name__}). The file may be corrupt.")
    total = sum(len(p.strip()) for p in pages)
    if total < 40:
        raise DocumentError(
            "This PDF has no extractable text - it looks like a scanned/image-based document. "
            "OCR is required (not enabled in this build). Export a text-based PDF, or upload DOCX/TXT.")
    blank = sum(1 for p in pages if len(p.strip()) < 10)
    if blank > len(pages) * 0.3:
        warnings.append(f"{blank} of {len(pages)} pages contain almost no text (possible scanned pages).")
    return pages


def _load_docx(data: bytes, warnings: list):
    try:
        import docx
        document = docx.Document(io.BytesIO(data))
    except ImportError:
        raise DocumentError("python-docx is not installed: pip install python-docx")
    except Exception as exc:
        raise DocumentError(f"Could not read the DOCX ({exc.__class__.__name__}).")
    pages, current, explicit = [], [], False
    for para in document.paragraphs:
        has_break = "w:br" in para._p.xml and 'w:type="page"' in para._p.xml
        current.append(para.text)
        if has_break:
            explicit = True
            pages.append("\n".join(current))
            current = []
    if current:
        pages.append("\n".join(current))
    if not explicit:
        pages = _paginate("\n".join(p for p in pages))
        return pages, "estimated"
    return pages, "actual"


def load_document(filename: str, data: bytes, max_mb: int = 15) -> LoadedDocument:
    ext = validate_upload(filename, len(data), max_mb)
    warnings, basis = [], "actual"
    if ext == ".pdf":
        pages = _load_pdf(data, warnings)
    elif ext == ".docx":
        pages, basis = _load_docx(data, warnings)
    else:
        text = _decode(data)
        if "\f" in text:
            pages = _paginate(text)
        else:
            pages, basis = _paginate(text), "estimated"
    if not any(p.strip() for p in pages):
        raise DocumentError("No text could be extracted from the document.")
    if basis == "estimated":
        warnings.append(f"Page numbers are estimated (~{LINES_PER_PAGE} lines per page) because the file has no page breaks.")
    return LoadedDocument(filename=filename, file_type=ext.lstrip("."), sha256=hashlib.sha256(data).hexdigest(),
                          size_bytes=len(data), pages=pages, warnings=warnings, page_basis=basis)

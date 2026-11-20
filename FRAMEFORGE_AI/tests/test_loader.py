import io

from core.document_loader import DocumentError, load_document
from tests.helpers import make_script


def _raises(fn):
    try:
        fn()
    except DocumentError as e:
        return str(e)
    raise AssertionError("expected DocumentError")


def test_txt():
    d = load_document("a.txt", make_script(5).encode())
    assert d.page_count >= 1 and "INT." in d.text and d.page_basis == "estimated"


def test_docx():
    import docx
    doc = docx.Document()
    for line in make_script(4).split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    assert "INT." in load_document("a.docx", buf.getvalue()).text


def _pdf(text_lines):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for ln in text_lines:
        c.drawString(50, y, ln)
        y -= 14
        if y < 50:
            c.showPage()
            y = 800
    c.save()
    return buf.getvalue()


def test_pdf_text_and_scanned():
    d = load_document("a.pdf", _pdf(make_script(6).split("\n")))
    assert "INT." in d.text and d.page_basis == "actual"
    msg = _raises(lambda: load_document("scan.pdf", _pdf([])))
    assert "OCR" in msg


def test_validation():
    assert "Unsupported" in _raises(lambda: load_document("a.exe", b"x"))
    assert "empty" in _raises(lambda: load_document("a.txt", b""))
    assert "limit" in _raises(lambda: load_document("a.txt", b"x" * 2_100_000, max_mb=2))

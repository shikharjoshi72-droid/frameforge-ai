"""ReportLab PDF generation: Black Book and single call sheets. Input is saved/validated data only."""
import io
import os
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, NextPageTemplate, PageBreak, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from config.constants import APP_NAME, DISCLAIMER
from config.settings import FONT_DIR

NAVY, ACCENT, VIOLET = colors.HexColor("#0F1B33"), colors.HexColor("#3D5AFE"), colors.HexColor("#6C4DFF")
ZEBRA, GRID, INK = colors.HexColor("#F2F4FA"), colors.HexColor("#C9CFE3"), colors.HexColor("#1B2238")
PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
AVAIL = PAGE_W - 2 * MARGIN
_FONTS = None


def _font_candidates():
    import reportlab
    rl = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
    return [
        (FONT_DIR / "DejaVuSans.ttf", FONT_DIR / "DejaVuSans-Bold.ttf", FONT_DIR / "DejaVuSans-Oblique.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/ariali.ttf"),
        ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf", "/Library/Fonts/Arial Italic.ttf"),
        (os.path.join(rl, "Vera.ttf"), os.path.join(rl, "VeraBd.ttf"), os.path.join(rl, "VeraIt.ttf")),
    ]


def register_fonts():
    """Register a Unicode TTF family; fall back to Helvetica (text is then sanitised to Latin-1)."""
    global _FONTS
    if _FONTS:
        return _FONTS
    for reg, bold, ital in _font_candidates():
        if all(os.path.exists(str(p)) for p in (reg, bold, ital)):
            try:
                pdfmetrics.registerFont(TTFont("FF", str(reg)))
                pdfmetrics.registerFont(TTFont("FF-B", str(bold)))
                pdfmetrics.registerFont(TTFont("FF-I", str(ital)))
                pdfmetrics.registerFontFamily("FF", normal="FF", bold="FF-B", italic="FF-I", boldItalic="FF-B")
                _FONTS = {"regular": "FF", "bold": "FF-B", "italic": "FF-I", "unicode": True}
                return _FONTS
            except Exception:
                continue
    _FONTS = {"regular": "Helvetica", "bold": "Helvetica-Bold", "italic": "Helvetica-Oblique", "unicode": False}
    return _FONTS


def _txt(v) -> str:
    s = "" if v is None else str(v)
    if not register_fonts()["unicode"]:
        s = s.encode("latin-1", "replace").decode("latin-1")
    return s


def esc(v) -> str:
    return escape(_txt(v)).replace("\n", "<br/>")


def styles():
    f = register_fonts()
    base = dict(fontName=f["regular"], textColor=INK, alignment=TA_LEFT)
    return {
        "body": ParagraphStyle("body", fontSize=9.5, leading=13.5, spaceAfter=5, **base),
        "small": ParagraphStyle("small", fontSize=7.6, leading=9.6, **base),
        "smallb": ParagraphStyle("smallb", fontSize=7.6, leading=9.6, **{**base, "fontName": f["bold"]}),
        "th": ParagraphStyle("th", fontSize=7.8, leading=10, **{**base, "fontName": f["bold"], "textColor": colors.white}),
        "h1": ParagraphStyle("h1", fontSize=17, leading=21, spaceBefore=4, spaceAfter=8,
                             **{**base, "fontName": f["bold"], "textColor": NAVY}),
        "h2": ParagraphStyle("h2", fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=4,
                             **{**base, "fontName": f["bold"], "textColor": ACCENT}),
        "note": ParagraphStyle("note", fontSize=8, leading=11, **{**base, "fontName": f["italic"],
                                                                   "textColor": colors.HexColor("#555B73")}),
        "toc0": ParagraphStyle("toc0", fontSize=10, leading=17, **base),
    }


class H1(Paragraph):
    toc_level = 0


class BookTemplate(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if getattr(flowable, "toc_level", None) is not None:
            self.notify("TOCEntry", (flowable.toc_level, flowable.getPlainText(), self.page))


def _table(headers, rows, fracs, st, empty="No records."):
    if not rows:
        return Paragraph(esc(empty), st["note"])
    data = [[Paragraph(esc(h), st["th"]) for h in headers]]
    for r in rows:
        data.append([Paragraph(esc(c), st["small"]) for c in r])
    t = Table(data, colWidths=[AVAIL * f for f in fracs], repeatRows=1, splitByRow=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, GRID), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def _kv(pairs, st):
    return _table(["Field", "Value"], [[k, v if v not in (None, "") else "Not provided"] for k, v in pairs], [0.28, 0.72], st)


def _bullets(items, st, empty="Not available."):
    if not items:
        return [Paragraph(esc(empty), st["note"])]
    return [Paragraph("&bull; " + esc(i), st["body"]) for i in items]


def _call_sheet_flow(cs, st):
    fl = [Paragraph(esc(f"Day {cs['day_number']} - {cs['date']}  ({cs['status']})"), st["h2"]),
          _kv([("Production", cs["production"]), ("Reporting time", cs["call_time"]), ("Expected wrap", cs["wrap_time"]),
               ("Location", cs["location"]), ("Unit", cs.get("call_type")), ("Crew", cs["crew"]),
               ("Emergency contact", cs["emergency_contact"])], st), Spacer(1, 4),
          _table(["Sc", "Heading", "Pg", "Cast"], [[s["number"], s["heading"], s["pages"], s["cast"]] for s in cs["scenes"]],
                 [0.07, 0.5, 0.08, 0.35], st), Spacer(1, 4),
          _kv([("Required cast", ", ".join(cs["cast"])), ("Props", ", ".join(cs["props"])),
               ("Equipment", ", ".join(cs["equipment"])), ("Costume notes", ", ".join(cs["costumes"])),
               ("Special instructions", "\n".join(cs["special"]))], st)]
    return fl


def _cover(canvas, doc, b):
    f = register_fonts()
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    canvas.setFillColor(VIOLET)
    canvas.rect(0, PAGE_H * 0.58, PAGE_W, 3, stroke=0, fill=1)
    canvas.setFillColor(colors.HexColor("#9AA7FF"))
    canvas.setFont(f["bold"], 11)
    canvas.drawString(MARGIN, PAGE_H - 40 * mm, _txt(APP_NAME + "  |  PRODUCTION BLACK BOOK"))
    canvas.setFillColor(colors.white)
    canvas.setFont(f["bold"], 30)
    y = PAGE_H * 0.58 + 22 * mm
    for ln in reversed(simpleSplit(_txt(b["project"]["title"]).upper(), f["bold"], 30, AVAIL)[:4]):
        canvas.drawString(MARGIN, y, ln)
        y += 36
    canvas.setFont(f["regular"], 11)
    canvas.setFillColor(colors.HexColor("#C9D0F5"))
    y = PAGE_H * 0.58 - 14 * mm
    p = b["project"]
    for ln in [f"Project ID: {p['id']}", f"Document version: v{b['version']}",
               f"Generated: {b['generated_at']}", f"Review status: {p.get('review_status') or 'DRAFT'}",
               f"Director: {p.get('director') or 'Not provided'}",
               f"Production company: {p.get('company') or 'Not provided'}"]:
        canvas.drawString(MARGIN, y, _txt(ln))
        y -= 16
    canvas.setFont(f["italic"], 8)
    canvas.setFillColor(colors.HexColor("#9AA7FF"))
    for i, ln in enumerate(simpleSplit(_txt("AI-GENERATED INFORMATION: " + DISCLAIMER), f["italic"], 8, AVAIL)):
        canvas.drawString(MARGIN, 30 * mm - i * 10, ln)
    canvas.restoreState()


def _page(canvas, doc, b):
    f = register_fonts()
    canvas.saveState()
    canvas.setStrokeColor(GRID)
    canvas.line(MARGIN, PAGE_H - 12 * mm, PAGE_W - MARGIN, PAGE_H - 12 * mm)
    canvas.line(MARGIN, 13 * mm, PAGE_W - MARGIN, 13 * mm)
    canvas.setFont(f["bold"], 8)
    canvas.setFillColor(NAVY)
    canvas.drawString(MARGIN, PAGE_H - 10 * mm, _txt(b["project"]["title"])[:70])
    canvas.setFont(f["regular"], 8)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 10 * mm, f"{APP_NAME} - Black Book v{b['version']}")
    canvas.setFillColor(colors.HexColor("#555B73"))
    canvas.drawString(MARGIN, 8.5 * mm, _txt(f"{b['project']['id']}  |  {b['project'].get('review_status') or 'DRAFT'}  |  AI-assisted draft - verify before use"))
    canvas.drawRightString(PAGE_W - MARGIN, 8.5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_blackbook(b: dict, target) -> list:
    """Render the Black Book to `target` (path or file object). Returns the ordered list of section titles."""
    st = styles()
    buf = target
    doc = BookTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=18 * mm, bottomMargin=19 * mm,
                       title=_txt(b["project"]["title"] + " - Production Black Book"), author=APP_NAME)
    frame = Frame(MARGIN, 19 * mm, AVAIL, PAGE_H - 37 * mm, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    cover_frame = Frame(MARGIN, MARGIN, AVAIL, 10, id="c")
    doc.addPageTemplates([PageTemplate(id="cover", frames=[cover_frame], onPage=lambda c, d: _cover(c, d, b)),
                          PageTemplate(id="main", frames=[frame], onPage=lambda c, d: _page(c, d, b))])
    p, a, sc = b["project"], b["analysis"], b["scenes"]
    sections = []
    story = [NextPageTemplate("main"), PageBreak()]
    toc = TableOfContents()
    toc.levelStyles = [st["toc0"]]
    story += [Paragraph("Contents", st["h1"]), toc, PageBreak()]

    def section(title, flow):
        sections.append(title)
        story.append(H1(esc(f"{len(sections)}. {title}"), st["h1"]))
        story.extend(flow)
        story.append(PageBreak())

    section("Project Information", [_kv([
        ("Title", p["title"]), ("Project ID", p["id"]), ("Production company", p.get("company")),
        ("Director", p.get("director")), ("Genre", p.get("genre")), ("Target runtime (min)", p.get("target_runtime")),
        ("Production start date", p.get("start_date")), ("Description", p.get("description")),
        ("Review status", p.get("review_status")), ("Document version", f"v{b['version']}"),
        ("Generated", b["generated_at"]), ("Scenes / characters / locations",
                                           f"{len(sc)} / {len(b['characters'])} / {len(b['locations'])}")], st),
        Spacer(1, 8), Paragraph(esc("AI disclaimer: " + DISCLAIMER), st["note"])])

    section("Story Overview", [Paragraph("Synopsis", st["h2"]), Paragraph(esc(a.get("synopsis") or "Not generated."), st["body"]),
                                _kv([("Genre", a.get("genre") or p.get("genre")), ("Main plot", a.get("main_plot")),
                                     ("Protagonist", a.get("protagonist")), ("Antagonist", a.get("antagonist")),
                                     ("Supporting characters", ", ".join(a.get("supporting_characters", [])))], st),
                                Paragraph("Subplots", st["h2"]), *_bullets(a.get("subplots"), st),
                                Paragraph("Uncertainty notes", st["h2"]), *_bullets(a.get("uncertainty_notes"), st, "None recorded.")])

    section("Story Structure", [
        Paragraph("Beginning", st["h2"]), Paragraph(esc(a.get("beginning") or "Not available."), st["body"]),
        Paragraph("Middle", st["h2"]), Paragraph(esc(a.get("middle") or "Not available."), st["body"]),
        Paragraph("Ending", st["h2"]), Paragraph(esc(a.get("ending") or "Not available."), st["body"]),
        Paragraph("Major events", st["h2"]), *_bullets(a.get("major_events"), st),
        Paragraph("Turning points", st["h2"]), *_bullets(a.get("turning_points"), st),
        Paragraph("Emotional / dramatic sequences", st["h2"]), *_bullets(a.get("emotional_sequences"), st),
        Paragraph("Runtime estimate", st["h2"]),
        Paragraph(esc(f"~{a['runtime_estimate_min']} min. {a.get('runtime_basis', '')}" if a.get("runtime_estimate_min")
                      else "No defensible estimate available."), st["body"])])

    section("Character Register", [_table(
        ["Name", "Type / role", "Description", "Scenes", "First-last", "Costume / notes"],
        [[c["name"], f"{c['char_type'] or '-'} / {c['role'] or '-'}", c["description"], c["appearances"],
          f"{c['first_scene']}-{c['last_scene']}", "; ".join(x for x in (c["costume_notes"], c["notes"]) if x)]
         for c in b["characters"]], [0.13, 0.14, 0.27, 0.09, 0.10, 0.27], st)])

    def scene_row(s):
        flag = "\n[REVIEW] " + s["review_reason"] if s["needs_review"] else ""
        return [s["scene_number"], f"{s['heading']}{flag}", s["page_ref"], f"{s['int_ext']} / {s['time_of_day']}",
                ", ".join(s["characters"]), (s["description"] or "") + (f"\nAction: {s['main_action']}" if s["main_action"] else ""),
                f"{s['complexity']} ({int((s['confidence'] or 0) * 100)}%)"]
    section("Complete Scene Breakdown", [_table(["Sc", "Heading", "Pg", "I/E - D/N", "Characters", "Description", "Cplx (conf.)"],
                                                [scene_row(s) for s in sc], [0.05, 0.19, 0.06, 0.10, 0.17, 0.33, 0.10], st)])

    section("Location Register", [_table(
        ["Location", "I/E", "Day/Night", "Scenes", "Props", "Cplx", "Notes"],
        [[l["name"], l["int_ext"], l["day_night"], l["scene_numbers"], l["props"], l["complexity"],
          "; ".join(x for x in (l["description"], l["notes"], l["duplicate_hint"]) if x)] for l in b["locations"]],
        [0.14, 0.09, 0.13, 0.12, 0.17, 0.08, 0.27], st)])

    def res_table(cat):
        rows = [[r["name"], r["scene_uids"], r["source_type"], r["quantity"] or "", "; ".join(x for x in (r["description"], r["notes"]) if x)]
                for r in b["resources"] if r["category"] == cat]
        return _table(["Item", "Scenes", "Source", "Qty", "Description / notes"], rows, [0.22, 0.14, 0.12, 0.07, 0.45], st,
                      f"No {cat.lower()} records.")
    section("Props Register", [res_table("Prop")])
    section("Costume Register", [res_table("Costume")])
    section("Equipment Register", [res_table("Equipment"), Paragraph("Vehicles", st["h2"]), res_table("Vehicle"),
                                    Paragraph("Special effects", st["h2"]), res_table("Special Effect"),
                                    Paragraph("Other requirements", st["h2"]), res_table("Other")])

    sched = b["schedule"]
    sflow = [Paragraph(esc(f"Status: {'APPROVED by the production team' if sched['approved'] else 'PROPOSED - not approved. Dates, availability and bookings are unconfirmed.'}"), st["note"]), Spacer(1, 4)]
    sflow.append(_table(["Day", "Date", "Unit", "Location(s)", "Scenes", "Est. min", "Rationale"],
                        [[d["day_number"], d["shoot_date"] or "Pending", d["call_type"], d["location_names"],
                          ", ".join(str(s["scene_number"]) for s in d["scenes"]), d["est_minutes"], d["explanation"]]
                         for d in sched["days"]], [0.06, 0.11, 0.07, 0.17, 0.13, 0.08, 0.38], st, "No schedule generated."))
    section("Shooting Schedule", sflow)

    cflow = []
    for d in sched["days"]:
        cflow += _call_sheet_flow(d["call_sheet"], st) + [Spacer(1, 10)]
    section("Daily Call Sheets", cflow or [Paragraph("No call sheets - generate a schedule first.", st["note"])])

    pr = b["progress"]
    section("Production Summary", [_kv([
        ("Total scenes", pr["total"]), ("Completed scenes", pr["completed"]), ("Pending scenes", pr["pending"]),
        ("Completion", f"{pr['pct']}%"), ("Shooting days planned", pr["days_planned"]),
        ("Shooting days completed", pr["days_completed"]), ("Locations covered", pr["locations_covered"]),
        ("Scene status counts", ", ".join(f"{k}: {v}" for k, v in pr["counts"].items()))], st)])

    section("Pending Information", _bullets(b["pending"], st, "No outstanding items detected."))
    section("Production Notes", [Paragraph(esc(p.get("notes") or "No production notes recorded."), st["body"]),
                                  Paragraph("Scenes flagged for review", st["h2"]),
                                  *_bullets([f"Sc {s['scene_number']} ({s['heading']}): {s['review_reason']}" for s in sc if s["needs_review"]],
                                            st, "None.")])
    story.pop()  # trailing page break
    doc.multiBuild(story)
    return ["Cover Page"] + sections


def build_call_sheet_pdf(cs: dict) -> bytes:
    st = styles()
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=16 * mm, bottomMargin=16 * mm,
                          title=_txt(f"Call Sheet - {cs['production']} - Day {cs['day_number']}"), author=APP_NAME)
    doc.addPageTemplates([PageTemplate(id="m", frames=[Frame(MARGIN, 16 * mm, AVAIL, PAGE_H - 32 * mm, id="f")])])
    flow = [Paragraph(esc(f"{cs['production']} - DAILY CALL SHEET"), st["h1"])] + _call_sheet_flow(cs, st) + \
           [Spacer(1, 8), Paragraph(esc("Fields marked PENDING were not supplied. " + DISCLAIMER), st["note"])]
    doc.build(flow)
    return buf.getvalue()


def verify_pdf(path_or_bytes, expected_titles: list) -> dict:
    """Open the PDF, count pages, and confirm every section title appears in the extracted text."""
    data = path_or_bytes if isinstance(path_or_bytes, bytes) else open(path_or_bytes, "rb").read()
    res = {"ok": data[:5] == b"%PDF-", "pages": None, "missing": list(expected_titles), "checked": False}
    text = None
    try:
        import fitz
        with fitz.open(stream=data, filetype="pdf") as d:
            res["pages"] = len(d)
            text = "\n".join(pg.get_text() for pg in d)
    except ImportError:
        try:
            from pypdf import PdfReader
            r = PdfReader(io.BytesIO(data))
            res["pages"] = len(r.pages)
            text = "\n".join((pg.extract_text() or "") for pg in r.pages)
        except Exception:
            pass
    except Exception:
        res["ok"] = False
    if text is not None:
        res["checked"] = True
        low = text.lower()
        res["missing"] = [t for t in expected_titles if t.lower() not in low]
        res["ok"] = res["ok"] and not res["missing"]
    return res

from core.chunking_engine import build_chunks, extract_speakers, match_heading, parse_heading, segment
from core.text_preprocessor import clean_page
from tests.helpers import make_script


def pages_of(text, per=50):
    lines = text.split("\n")
    return ["\n".join(lines[i:i + per]) for i in range(0, len(lines), per)]


def test_heading_parsing():
    h = parse_heading("12 INT. COFFEE SHOP - COUNTER - NIGHT 12")
    assert (h["scene_no"], h["int_ext"], h["time_of_day"], h["location"]) == ("12", "INT", "NIGHT", "COFFEE SHOP - COUNTER")
    assert parse_heading("EXT./INT. CAR - DAY")["int_ext"] == "INT/EXT"
    assert match_heading("Interior of the house is dark.") is None
    assert parse_heading("INT. LAB - LATER")["time_of_day"] == "CONTINUOUS"
    assert parse_heading("INT. HALL")["time_of_day"] == "UNKNOWN"


def test_segment_counts_and_order():
    blocks, info = segment(pages_of(make_script(30)))
    assert len(blocks) == 30 and info["headings_found"] == 30
    assert [b.block_id for b in blocks] == [f"B{i:03d}" for i in range(1, 31)]
    assert info["skipped_front_matter_chars"] > 0


def test_no_headings_flagged():
    blocks, info = segment(["Just some prose without any headings.\n" * 100])
    assert info["mode"] == "no_headings" and blocks and all(b.flag for b in blocks) and not any(b.heading_ok for b in blocks)


def test_chunks_preserve_order_and_blocks():
    blocks, _ = segment(pages_of(make_script(30)))
    chunks = build_chunks(blocks, max_chars=1200, max_blocks=5, context_chars=200)
    seen = [u["block_id"] for c in chunks for u in c.units]
    assert seen == [b.block_id for b in blocks]
    assert len(chunks) > 1 and chunks[0].context == "" and chunks[1].context


def test_long_scene_is_split_not_dropped():
    long_scene = "INT. WAREHOUSE - NIGHT\n\n" + "\n\n".join(f"Paragraph {i} " + "x" * 400 for i in range(30))
    blocks, _ = segment([long_scene + "\n\nINT. OFFICE - DAY\n\nShort."])
    chunks = build_chunks(blocks, max_chars=3000, max_blocks=8)
    parts = [u for c in chunks for u in c.units if u["block_id"] == "B001"]
    assert len(parts) > 1 and "".join(u["text"] for u in parts).count("Paragraph") == 30


def test_speaker_detection():
    sp = extract_speakers("INT. ROOM - DAY\n\nMAYA\nHello.\n\nDEV (V.O.)\nHi.\n\nCUT TO:\n\nShe smiles.")
    assert sp == {"MAYA": "", "DEV": "voice"}


def test_clean_page_removes_page_numbers():
    out = clean_page("12.\nINT. A - DAY\nline\nline\n(CONTINUED)\nmore\n13")
    assert "12." not in out.split("\n")[0] and "CONTINUED" not in out

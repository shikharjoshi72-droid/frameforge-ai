"""Screenplay upload, validation, duplicate detection, extraction preview."""
import re
from pathlib import Path

import streamlit as st

from config.settings import UPLOAD_DIR, get_settings
from core.document_loader import DocumentError, load_document
from core.text_preprocessor import clean_pages
from ui import theme


def render_upload(repo, pid):
    st.caption("Supported: PDF, DOCX, TXT. The original file and its extracted text are stored with the project.")
    file = st.file_uploader("Upload the complete screenplay", type=["pdf", "docx", "txt"], key=f"up_{pid}")
    if file is not None and st.button("Save & extract text", type="primary"):
        try:
            loaded = load_document(file.name, file.getvalue(), get_settings().max_upload_mb)
        except DocumentError as exc:
            st.error(str(exc))
        else:
            dup = repo.find_document_by_hash(pid, loaded.sha256)
            if dup:
                st.warning(f"This exact file was already uploaded as '{dup['filename']}' on {dup['created_at'][:10]}. Not stored again.")
            else:
                folder = UPLOAD_DIR / pid
                folder.mkdir(parents=True, exist_ok=True)
                stored = folder / f"{loaded.sha256[:10]}_{re.sub(r'[^A-Za-z0-9._-]', '_', file.name)}"
                stored.write_bytes(file.getvalue())
                repo.add_document(pid, "screenplay", file.name, loaded.sha256, loaded.size_bytes, loaded.page_count,
                                  str(stored), loaded.text, loaded.pages, loaded.warnings)
                st.success(f"Extracted {loaded.page_count} page(s) from {file.name}.")
                for w in loaded.warnings:
                    st.warning(w)
    doc = repo.latest_document(pid)
    if not doc:
        theme.empty("No screenplay uploaded", "Upload a text-based PDF, DOCX or TXT screenplay to begin.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("File", doc["filename"])
    c2.metric("Pages", doc["page_count"])
    c3.metric("Characters of text", f"{len(doc['extracted_text'] or ''):,}")
    for w in doc["warnings"]:
        st.warning(w)
    text = "\n\n".join(clean_pages(doc["pages"]))
    st.text_area("Extracted screenplay text (cleaned preview, read before analysing)", text[:60000], height=360, disabled=True)
    if len(text) > 60000:
        st.caption("Preview truncated to the first 60,000 characters; the full text is analysed.")

"""Text cleaning that preserves screenplay structure."""
import re

_PAGE_NUM = re.compile(r"^\s*\d{1,3}\.?\s*$")
_CONTINUED = re.compile(r"^\s*\d*[A-Z]?\s*\(?(CONTINUED|MORE)(?::|\))?\s*\(?\d*[A-Z]?\)?\s*$", re.I)


def clean_page(text: str) -> str:
    text = (text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
            .replace("\u00ad", "").replace("\ufeff", "").replace("\t", "    "))
    lines = [ln.rstrip() for ln in text.split("\n")]
    nonempty = [i for i, ln in enumerate(lines) if ln.strip()]
    # drop a bare page number at the very top or bottom of the page
    for idx in (nonempty[:1] + nonempty[-1:]):
        if len(nonempty) > 3 and _PAGE_NUM.match(lines[idx]):
            lines[idx] = ""
    lines = [ln for ln in lines if not _CONTINUED.match(ln)]
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return out.strip("\n")


def clean_pages(pages: list) -> list:
    return [clean_page(p) for p in pages]

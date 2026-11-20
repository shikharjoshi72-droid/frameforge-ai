"""Premium dark cinematic theme."""
import streamlit as st

CSS = """
<style>
:root { --bg:#0B1020; --panel:#121A30; --panel2:#18223D; --line:#26325A; --text:#E6EAF8; --muted:#8C97BD;
        --blue:#4C6FFF; --violet:#7B5CFF; }
.stApp { background: var(--bg); color: var(--text); }
section[data-testid="stSidebar"] { background: #0A0F1E; border-right: 1px solid var(--line); }
h1,h2,h3 { color: var(--text); letter-spacing: .2px; }
.ff-brand { font-size: 1.35rem; font-weight: 800; letter-spacing: 1.5px; color: #fff; }
.ff-brand span { color: var(--violet); }
.ff-sub { font-size: .62rem; letter-spacing: 2px; color: var(--muted); margin-bottom: .6rem; }
.ff-card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.ff-metric { background: linear-gradient(180deg, var(--panel), var(--panel2)); border: 1px solid var(--line);
             border-radius: 12px; padding: 14px 16px; }
.ff-metric .v { font-size: 1.8rem; font-weight: 700; color: #fff; }
.ff-metric .l { font-size: .72rem; letter-spacing: 1.2px; color: var(--muted); text-transform: uppercase; }
.ff-pill { display:inline-block; padding: 2px 10px; border-radius: 999px; font-size: .72rem; border: 1px solid var(--line); }
.ff-ok { color:#7CE3A1; border-color:#2C6B4A; } .ff-bad { color:#FF8A8A; border-color:#7A3030; }
.ff-warn { color:#FFD27C; border-color:#7A6330; } .ff-run { color:#9AB0FF; border-color:#34457F; }
.ff-empty { text-align:center; padding: 48px 12px; border: 1px dashed var(--line); border-radius: 14px; color: var(--muted); }
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] { border: 1px solid var(--line); border-radius: 10px; }
.stButton>button, .stDownloadButton>button { border-radius: 8px; border: 1px solid var(--line); }
.stButton>button[kind="primary"], .stDownloadButton>button[kind="primary"] { background: linear-gradient(90deg, var(--blue), var(--violet)); border: none; }
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def metric(label, value):
    st.markdown(f'<div class="ff-metric"><div class="v">{value}</div><div class="l">{label}</div></div>', unsafe_allow_html=True)


def pill(text, kind="run"):
    return f'<span class="ff-pill ff-{kind}">{text}</span>'


def empty(title, body=""):
    st.markdown(f'<div class="ff-empty"><div style="font-size:1.4rem;color:#E6EAF8">{title}</div><div>{body}</div></div>',
                unsafe_allow_html=True)

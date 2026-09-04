"""Shared visual theme for every Streamlit page in the studio."""

import streamlit as st


THEME_CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Prompt:wght@400;500;600;700&display=swap');

:root {
  --ink: #352b4f;
  --muted: #756b8f;
  --purple: #7c5cff;
  --purple-dark: #6647e8;
  --pink: #ff72ad;
  --mint: #55d6be;
  --peach: #ffb780;
  --surface: rgba(255, 255, 255, .86);
  --line: rgba(124, 92, 255, .14);
  --shadow: 0 14px 40px rgba(76, 54, 130, .11);
}

html, body, [class*="css"], .stApp {
  font-family: "Nunito", "Prompt", sans-serif;
  color: var(--ink);
}

.stApp {
  background:
    radial-gradient(circle at 8% 5%, rgba(255, 174, 211, .38), transparent 26rem),
    radial-gradient(circle at 92% 12%, rgba(170, 229, 255, .36), transparent 28rem),
    linear-gradient(145deg, #fff9fd 0%, #f7f5ff 52%, #f2fbff 100%);
}

.stMainBlockContainer { max-width: 1380px; padding-top: 2.1rem; padding-bottom: 4rem; }
h1, h2, h3 { color: var(--ink) !important; letter-spacing: -.02em; }
h1 { font-weight: 900 !important; }
h2, h3 { font-weight: 800 !important; }
p, label, .stMarkdown { color: var(--ink); }

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(255,255,255,.97), rgba(246,241,255,.97));
  border-right: 1px solid var(--line);
  box-shadow: 10px 0 35px rgba(76,54,130,.07);
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: 1rem; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: var(--purple-dark) !important; }
[data-testid="stSidebarNav"] a { border-radius: 14px; margin: 4px 8px; font-weight: 700; }
[data-testid="stSidebarNav"] a:hover { background: #eee9ff; color: var(--purple-dark); }
[data-testid="stSidebarNav"] a[aria-current="page"] {
  background: linear-gradient(135deg, var(--purple), #9a7cff);
  color: white !important;
  box-shadow: 0 8px 20px rgba(124,92,255,.25);
}

.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  border: 0 !important;
  border-radius: 14px !important;
  background: linear-gradient(135deg, var(--purple), var(--pink)) !important;
  color: white !important;
  font-weight: 800 !important;
  min-height: 2.85rem;
  box-shadow: 0 9px 22px rgba(124,92,255,.24);
  transition: transform .18s ease, box-shadow .18s ease, filter .18s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  transform: translateY(-2px);
  box-shadow: 0 13px 28px rgba(124,92,255,.31);
  filter: saturate(1.08);
}
.stButton > button:active, .stDownloadButton > button:active { transform: translateY(0); }

[data-baseweb="input"] > div, [data-baseweb="textarea"] > div,
[data-baseweb="select"] > div, [data-testid="stNumberInput"] > div > div {
  background: rgba(255,255,255,.9) !important;
  border-color: rgba(124,92,255,.18) !important;
  border-radius: 13px !important;
}
[data-baseweb="input"] > div:focus-within, [data-baseweb="textarea"] > div:focus-within,
[data-baseweb="select"] > div:focus-within {
  border-color: var(--purple) !important;
  box-shadow: 0 0 0 3px rgba(124,92,255,.12) !important;
}
[data-testid="stSlider"] [role="slider"] { background: var(--purple) !important; }
[data-testid="stCheckbox"] span[aria-checked="true"], [role="radiogroup"] span[aria-checked="true"] { background: var(--purple) !important; }

[data-testid="stMetric"] {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 22px;
  padding: 1.25rem 1.35rem;
  box-shadow: var(--shadow);
}
[data-testid="stMetricValue"] { color: var(--purple-dark); font-weight: 900; }

[data-testid="stAlert"] { border: 0; border-radius: 16px; box-shadow: 0 8px 24px rgba(76,54,130,.08); }
[data-testid="stExpander"] {
  background: rgba(255,255,255,.72);
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
}
hr { border-color: rgba(124,92,255,.12) !important; margin: 1.6rem 0 !important; }
iframe { border-radius: 22px; box-shadow: var(--shadow); }

.studio-hero {
  position: relative;
  overflow: hidden;
  padding: clamp(1.55rem, 4vw, 3rem);
  border-radius: 28px;
  color: white;
  background: linear-gradient(125deg, #7357ef 0%, #9a70f8 52%, #ff83b5 100%);
  box-shadow: 0 20px 55px rgba(111,76,210,.27);
  margin-bottom: 1.65rem;
}
.studio-hero:after {
  content: "✦"; position: absolute; right: 4%; top: -28%;
  font-size: 14rem; color: rgba(255,255,255,.11); transform: rotate(12deg);
}
.studio-hero .eyebrow { font-weight: 900; letter-spacing: .12em; text-transform: uppercase; opacity: .8; font-size: .78rem; }
.studio-hero h1 { color: white !important; margin: .35rem 0 .55rem; font-size: clamp(2rem, 4.4vw, 3.6rem); line-height: 1.06; }
.studio-hero p { color: rgba(255,255,255,.9); font-size: 1.08rem; max-width: 720px; margin: 0; }
.hero-pills { display:flex; flex-wrap:wrap; gap:.55rem; margin-top:1.2rem; }
.hero-pill { background:rgba(255,255,255,.17); border:1px solid rgba(255,255,255,.24); border-radius:999px; padding:.42rem .8rem; font-weight:800; font-size:.84rem; }

.login-wrap { max-width: 680px; margin: 1.5rem auto .8rem; text-align:center; }
.login-icon { width:76px; height:76px; display:grid; place-items:center; margin:0 auto 1rem; border-radius:24px; background:linear-gradient(135deg,#f0eaff,#ffe8f2); font-size:2.2rem; box-shadow:var(--shadow); }
.login-wrap h1 { margin-bottom:.35rem; }
.login-wrap p { color:var(--muted); font-size:1.05rem; }

.feature-card {
  min-height: 148px; padding: 1.25rem; border-radius: 20px;
  background: var(--surface); border: 1px solid var(--line); box-shadow: var(--shadow);
  transition: transform .18s ease;
}
.feature-card:hover { transform: translateY(-3px); }
.feature-icon { font-size: 1.7rem; }
.feature-card h3 { margin: .5rem 0 .25rem; font-size: 1.05rem; }
.feature-card p { color: var(--muted); margin: 0; font-size: .91rem; line-height: 1.5; }
.section-kicker { color: var(--purple-dark); font-weight:900; letter-spacing:.1em; text-transform:uppercase; font-size:.76rem; margin-bottom:.15rem; }
.footer-note { text-align:center; color:var(--muted); padding:1.4rem 0 .5rem; font-size:.9rem; }

@media (max-width: 700px) {
  .stMainBlockContainer { padding: 1rem .85rem 3rem; }
  .studio-hero { border-radius: 22px; padding: 1.45rem; }
  .studio-hero:after { font-size: 8rem; }
  [data-testid="stMetric"] { padding: 1rem; }
}
</style>
"""


def apply_theme() -> None:
    """Inject the shared theme once for the current Streamlit page."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


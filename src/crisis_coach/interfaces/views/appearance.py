"""Local CSS; no external fonts or simulated device telemetry."""
import streamlit as st


def render_appearance():
    theme = st.sidebar.radio("Appearance", ["Dark", "Light"], horizontal=True, key="appearance")
    dark = theme == "Dark"
    bg, panel, text, muted, accent = (("#101b21","#1b2b33","#f2f6f8","#b7c6ce","#ffbd66") if dark else ("#f2f5f4","#ffffff","#192d35","#455f6b","#885000"))
    st.markdown(f"""<style>
    .stApp {{ --cc-bg:{bg}; --cc-panel:{panel}; --cc-text:{text}; --cc-muted:{muted}; --cc-accent:{accent}; background:{bg}; color:{text}; font-family:Arial,sans-serif; }}
    [data-testid="stHeader"], [data-testid="stBottom"] {{ background:{bg}; }}
    [data-testid="stSidebar"] {{ background:{panel}; color:{text}; }}
    .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label, .stApp li, .stApp summary {{ color:{text}; }}
    .stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] *, .stApp small, .stApp small * {{ color:{muted} !important; opacity:1 !important; }}
    .stApp input::placeholder, .stApp textarea::placeholder {{ color:{muted} !important; opacity:1; }}
    .stApp [data-testid="stFileUploaderDropzone"], .stApp [data-testid="stChatInput"] {{ background:{panel}; color:{text}; border:1px solid {muted}; }}
    .stApp [data-testid="stChatInput"] textarea {{ background:{panel} !important; color:{text} !important; }}
    .stApp [data-testid="stSidebarCollapseButton"] *, .stApp [data-testid="stExpandSidebarButton"], .stApp [data-testid="stExpandSidebarButton"] * {{ color:{text} !important; }}
    .st-key-coach_card {{ border-top:4px solid {accent}; background:{panel}; border-radius:14px; padding:1.2rem; }}
    .stApp summary {{ background:{panel} !important; color:{text} !important; }}
    .stApp [data-testid="stFileUploaderDropzone"] * {{ color:{muted} !important; }}
    .stApp button {{ min-height:44px; }}
    .stApp button[kind="secondary"], .stApp button[kind="secondaryFormSubmit"] {{ background:{panel}; color:{text}; border:1px solid {muted}; }}
    .stApp input, .stApp textarea {{ color:{text}; background:{panel}; }}
    .stApp [data-baseweb="input"], .stApp [data-baseweb="textarea"], .stApp [data-baseweb="select"] > div {{ background:{panel}; color:{text}; }}
    .stApp button:focus-visible, .stApp input:focus-visible, .stApp textarea:focus-visible {{ outline:3px solid {accent}; outline-offset:3px; }}
    .stMainBlockContainer {{ max-width:1120px; padding-top:2rem; }}
    .stApp [data-testid="stChatMessage"] {{ background:{panel}; }}
    @media(max-width:640px) {{ .stMainBlockContainer {{ padding-left:1rem; padding-right:1rem; }} h1 {{ font-size:2rem !important; }} }}
    </style>""", unsafe_allow_html=True)

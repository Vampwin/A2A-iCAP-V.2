import base64
from pathlib import Path

import streamlit as st


@st.cache_data(show_spinner=False)
def _video_base64(path: str):
    p = Path(path)
    if not p.exists():
        return None
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def render_dynamic_logo(video_path: str, max_width: str = "560px", loop: bool = True) -> bool:
    """
    Render an autoplaying, muted, chrome-free logo animation centered in a
    soft rounded card. Returns False (renders nothing) if the file is missing,
    so callers can fall back to a static logo.
    """
    b64 = _video_base64(video_path)
    if not b64:
        return False
    loop_attr = "loop " if loop else ""
    st.markdown(
        f"""
        <div style="display:flex; justify-content:center; margin:0.2rem 0 1.1rem 0;">
          <div style="max-width:{max_width}; width:100%; border-radius:20px; overflow:hidden;
                      background:#FFFFFF; border:1px solid #D6EFEF;
                      box-shadow:0 10px 32px rgba(27,107,107,0.16);">
            <video autoplay muted {loop_attr}playsinline
                   style="display:block; width:100%; height:auto;">
              <source src="data:video/mp4;base64,{b64}" type="video/mp4">
            </video>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return True


def apply_poster_style():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: 1250px;
        }

        h1, h2, h3 {
            color: #1B6B6B;
            font-weight: 700;
        }

        .poster-box {
            background-color: #F8FBFB;
            border: 1px solid #D6EFEF;
            border-left: 7px solid #1B6B6B;
            border-radius: 14px;
            padding: 18px 20px;
            margin-bottom: 16px;
            font-size: 1.02rem;
        }

        .ml-box      { border-left-color: #E87722; }
        .docking-box { border-left-color: #2E5FA3; }
        .drug-box    { border-left-color: #3A7D44; }
        .consensus-box { border-left-color: #C9A84C; }

        div[data-testid="stMetric"] {
            background-color: #FFFFFF;
            border: 1px solid #D6EFEF;
            border-radius: 12px;
            padding: 12px;
        }

        div.stButton > button {
            border-radius: 10px;
            border: 1px solid #1B6B6B;
            color: #1B6B6B;
            font-weight: 600;
        }

        div.stButton > button[kind="primary"],
        div.stButton > button[data-testid="baseButton-primary"] {
            background-color: #1B6B6B;
            color: #FFFFFF !important;
            border: none;
        }

        div.stButton > button[kind="primary"]:hover,
        div.stButton > button[data-testid="baseButton-primary"]:hover {
            background-color: #145555;
            color: #FFFFFF !important;
        }

        div.stDownloadButton > button {
            border-radius: 10px;
            font-weight: 600;
        }

        .small-note {
            color: #4B5563;
            font-size: 0.95rem;
        }

        /* Tier badge styles */
        .tier1-badge {
            background: #D1FAE5; color: #065F46;
            padding: 3px 12px; border-radius: 20px;
            font-weight: 700; font-size: 0.92rem;
            border: 1.5px solid #6EE7B7;
        }
        .tier2-badge {
            background: #FEF3C7; color: #92400E;
            padding: 3px 12px; border-radius: 20px;
            font-weight: 700; font-size: 0.92rem;
            border: 1.5px solid #FCD34D;
        }
        .tier3-badge {
            background: #F3F4F6; color: #6B7280;
            padding: 3px 12px; border-radius: 20px;
            font-weight: 700; font-size: 0.92rem;
            border: 1.5px solid #D1D5DB;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

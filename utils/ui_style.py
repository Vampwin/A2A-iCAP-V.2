import base64
import html
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


_BADGE_TONES = {
    "good":    ("#D1FAE5", "#065F46", "#6EE7B7"),
    "warn":    ("#FEF3C7", "#92400E", "#FCD34D"),
    "bad":     ("#FEE2E2", "#991B1B", "#FCA5A5"),
    "info":    ("#DBEAFE", "#1E40AF", "#93C5FD"),
    "neutral": ("#F3F4F6", "#374151", "#D1D5DB"),
}


def status_badge(label: str, value, tone: str = "neutral", help_text: str = "") -> str:
    """
    Build one wrap-safe "label + colored pill" card as an HTML string, meant
    to replace st.metric() for short categorical results (e.g. "Predicted
    Active", "Inside AD", "Tier 1"). Unlike st.metric, the value text wraps
    instead of being clipped when it doesn't fit the column width.
    Combine several with render_badge_row().
    """
    bg, fg, border = _BADGE_TONES.get(tone, _BADGE_TONES["neutral"])
    value_str = html.escape("N/A" if value is None else str(value))
    label_str = html.escape(str(label))
    help_html = (
        f'<div style="font-size:0.74rem;color:#9CA3AF;margin-top:4px;line-height:1.3;">{html.escape(help_text)}</div>'
        if help_text else ""
    )
    # Built as one unbroken line (no embedded newlines/blank lines): when several of these
    # are joined together into a single st.markdown() call, a stray blank line in the middle
    # makes the markdown parser treat it as plain text instead of HTML past that point.
    return (
        '<div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:12px;padding:10px 14px;height:100%;">'
        f'<div style="font-size:0.78rem;color:#6B7280;margin-bottom:6px;">{label_str}</div>'
        f'<span style="display:inline-block;background:{bg};color:{fg};border:1.5px solid {border};'
        'padding:3px 12px;border-radius:20px;font-weight:700;font-size:0.92rem;'
        f'white-space:normal;word-break:break-word;line-height:1.3;">{value_str}</span>'
        f'{help_html}'
        '</div>'
    )


def render_badge_row(badges: list) -> None:
    """Render status_badge() cards in a responsive grid that wraps on narrow screens instead of clipping."""
    st.markdown(
        '<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); '
        'gap:10px; margin-bottom:14px; align-items:stretch;">' + "".join(badges) + "</div>",
        unsafe_allow_html=True,
    )


GLOSSARY = {
    "SMILES": "A text code used by software to store a molecule's chemical structure.",
    "CAS No.": "A unique ID number officially assigned to a chemical substance.",
    "PubChem CID": "The compound's ID number in PubChem, a free public chemistry database.",
    "AI activity signal": "The model's estimate that a compound may block the A₂A receptor. It is a screening signal, not laboratory proof.",
    "Model confidence (AD)": "Whether a molecule is similar enough to the model's training examples for the estimate to be used with confidence.",
    "Simulated target fit": "A computer estimate of how well a molecule may fit the receptor. It does not confirm binding in the laboratory.",
    "kcal/mol": "The unit used for the simulated fit score. A more negative number suggests a tighter predicted fit.",
    "LogP": "A measure of how well a compound dissolves in fat vs. water; affects how easily the body absorbs it.",
    "TPSA": "Topological Polar Surface Area — relates to how easily a compound can cross cell membranes.",
    "HBD / HBA": "Hydrogen Bond Donors / Acceptors — chemical groups that affect solubility and how a compound interacts with its target.",
    "Rotatable Bonds": "Bonds in a molecule that can spin freely; too many can make a drug less stable in the body.",
    "Shortlist score / Tier": "A transparent ranking built from AI, simulated fit, and early developability signals.",
}


def render_glossary_sidebar() -> None:
    """Persistent 'what do these terms mean' reference, collapsed by default in the sidebar."""
    with st.sidebar:
        with st.expander("❓ Glossary — what do these terms mean?"):
            for term, definition in GLOSSARY.items():
                st.markdown(f"**{term}**  \n<span style='color:#6B7280; font-size:0.88rem;'>{definition}</span>",
                            unsafe_allow_html=True)


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

        .decision-card {
            background:#FFFFFF;
            border:1px solid #D6EFEF;
            border-radius:16px;
            padding:20px;
            min-height:155px;
            box-shadow:0 6px 18px rgba(27,107,107,0.08);
            color:#374151;
            line-height:1.55;
        }

        .decision-card b {
            color:#1B6B6B;
            font-size:1.02rem;
        }

        .decision-icon {
            font-size:1.65rem;
            margin-bottom:8px;
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

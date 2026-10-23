"""
Job Stitch — Streamlit app
===========================
"Align Your Potential." Upload (or paste) a resume and a job description,
get a fit score, see which skills match and which are missing, get
AI-tailored suggestions, a rewritten resume as a downloadable PDF, a list
of similar organizations to research, and download the whole analysis as
a Word or PDF report.

Run locally:    streamlit run app.py
Deploy free:    https://share.streamlit.io  (see README.md)
"""

import os
from pathlib import Path

import streamlit as st
from PIL import Image

from resume_matcher.exporting import (
    build_docx_report,
    build_pdf_report,
    build_updated_resume_pdf,
)
from resume_matcher.matching import compute_match
from resume_matcher.parsing import (
    UnsupportedFileTypeError,
    parse_pasted_text,
    parse_uploaded_file,
)
from resume_matcher.suggestions import (
    generate_ai_suggestions,
    generate_rule_based_suggestions,
    generate_similar_organizations,
    generate_updated_resume,
    get_verdict,
)

_ASSETS_DIR = Path(__file__).parent / "assets"
_ICON = Image.open(_ASSETS_DIR / "icon.png")

# Fixed provider: the app ships with a built-in Groq key (free tier) so
# visitors never have to find or paste in their own API key. Set via
# Streamlit's Secrets manager in the Cloud app's settings (key
# GROQ_API_KEY) -- never committed to the repo. Falls back to an
# environment variable of the same name for local runs.
_AI_PROVIDER = "groq"


def _get_builtin_api_key() -> str:
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        key = ""
    return key or os.environ.get("GROQ_API_KEY", "")


st.set_page_config(page_title="Job Stitch", page_icon=_ICON, layout="wide")

st.markdown(
    """
    <style>
    .jobstitch-title {
        font-size: 2.6rem;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 0;
    }
    /* Colors sampled directly from the Job Stitch logo artwork (assets/logo.png)
       so the on-page title matches it exactly: "Job" in a light silvery
       lavender-to-muted-purple gradient, "Stitch" in a lavender-to-deep-violet
       gradient. */
    .jobstitch-title .word-job {
        background: linear-gradient(180deg, #F3E9FB 0%, #9B8FC2 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        color: transparent;
    }
    .jobstitch-title .word-stitch {
        background: linear-gradient(180deg, #E8C8F5 0%, #4B0FC8 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        color: transparent;
        filter: drop-shadow(0 0 6px rgba(193, 60, 255, 0.55));
    }
    .jobstitch-tagline {
        color: #C13CFF;
        font-weight: 600;
        font-size: 1.05rem;
        margin-top: -4px;
        text-shadow: 0 0 10px rgba(193, 60, 255, 0.6);
    }
    .jobstitch-header-text {
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        height: 150px;
    }

    /* Luminous purple buttons (Analyze fit, downloads, Update as per
       requirement, Find similar organizations) with a glow on hover. */
    .stButton button, .stDownloadButton button {
        background-color: #C13CFF !important;
        color: #FFFFFF !important;
        border: 1px solid #C13CFF !important;
        transition: box-shadow 0.2s ease, background-color 0.2s ease;
    }
    .stButton button:hover, .stDownloadButton button:hover {
        background-color: #D264FF !important;
        border-color: #D264FF !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 16px rgba(193, 60, 255, 0.85), 0 0 32px rgba(193, 60, 255, 0.55);
    }
    .stButton button:active, .stDownloadButton button:active {
        background-color: #A52BE0 !important;
        border-color: #A52BE0 !important;
    }
    .stButton button:focus:not(:active), .stDownloadButton button:focus:not(:active) {
        color: #FFFFFF !important;
        border-color: #C13CFF !important;
        box-shadow: 0 0 10px rgba(193, 60, 255, 0.6);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_document_text(label: str, key_prefix: str):
    """Renders an upload-or-paste widget pair and returns (text, source_name)."""
    mode = st.radio(
        f"How do you want to provide your {label}?",
        ["Upload file", "Paste text"],
        key=f"{key_prefix}_mode",
        horizontal=True,
    )
    if mode == "Upload file":
        uploaded = st.file_uploader(
            f"Upload {label} (PDF, DOCX, or TXT)",
            type=["pdf", "docx", "txt"],
            key=f"{key_prefix}_file",
        )
        if uploaded is None:
            return None, None
        try:
            doc = parse_uploaded_file(uploaded)
        except UnsupportedFileTypeError as exc:
            st.error(str(exc))
            return None, None
        if not doc.text:
            st.warning(
                f"Couldn't extract any text from {uploaded.name}. "
                "If it's a scanned/image-based PDF, try pasting the text instead."
            )
            return None, None
        return doc.text, doc.source_name
    else:
        text = st.text_area(f"Paste your {label} text here", height=250, key=f"{key_prefix}_text")
        if not text.strip():
            return None, None
        doc = parse_pasted_text(text, label=f"Pasted {label}")
        return doc.text, doc.source_name


header_icon_col, header_title_col = st.columns([1, 6])
with header_icon_col:
    st.image(str(_ASSETS_DIR / "icon.png"), width=150)
with header_title_col:
    st.markdown(
        '<div class="jobstitch-header-text">'
        '<div class="jobstitch-title">'
        '<span class="word-job">Job</span> '
        '<span class="word-stitch">Stitch</span>'
        "</div>"
        '<div class="jobstitch-tagline">Align Your Potential.</div>'
        "</div>",
        unsafe_allow_html=True,
    )
st.write(
    "Upload a resume and a job description to see how well they match, "
    "what's missing, and how to improve your resume before you apply."
)

col1, col2 = st.columns(2)
with col1:
    st.subheader("1. Your resume")
    resume_text, resume_name = get_document_text("resume", "resume")
with col2:
    st.subheader("2. Job description")
    jd_text, jd_name = get_document_text("job description", "jd")

st.divider()

st.subheader("🤖 AI-Powered Tools")
st.caption(
    "Tailored suggestions, a resume rewritten for this job, and a list of "
    "similar organizations — included free, no API key needed from you."
)

ai_provider = _AI_PROVIDER
ai_api_key = _get_builtin_api_key()

if not ai_api_key:
    st.warning(
        "⚠️ AI-powered tools are temporarily unavailable (no API key "
        "configured for this app). The match score and suggestions below "
        "still work fully — only the AI-written suggestions, resume "
        "rewrite, and similar-organizations list are affected."
    )

analyze_clicked = st.button("🔍 Analyze fit", type="primary", use_container_width=True)

if analyze_clicked:
    if not resume_text or not jd_text:
        st.error("Please provide both a resume and a job description first.")
    else:
        with st.spinner("Analyzing..."):
            match = compute_match(resume_text, jd_text)
            verdict = get_verdict(match.overall_score)
            tips = generate_rule_based_suggestions(resume_text, match)

            ai_text = None
            if ai_api_key:
                try:
                    with st.spinner("Asking the AI for tailored suggestions..."):
                        ai_text = generate_ai_suggestions(
                            resume_text, jd_text, match, ai_provider, ai_api_key
                        )
                except RuntimeError as exc:
                    st.warning(str(exc))

        st.session_state["last_result"] = {
            "resume_text": resume_text,
            "resume_name": resume_name,
            "jd_text": jd_text,
            "jd_name": jd_name,
            "match": match,
            "verdict": verdict,
            "tips": tips,
            "ai_text": ai_text,
        }
        # Clear any previously generated resume rewrite / org list, since
        # they're tied to the previous analysis.
        st.session_state.pop("updated_resume_pdf", None)
        st.session_state.pop("similar_orgs_text", None)

if "last_result" in st.session_state:
    r = st.session_state["last_result"]
    match, verdict = r["match"], r["verdict"]

    st.header("Results")

    score_col, band_col = st.columns([1, 2])
    with score_col:
        st.metric("Overall Match Score", f"{match.overall_score}/100")
    with band_col:
        st.subheader(verdict.label)
        st.write(verdict.message)

    st.progress(min(int(match.overall_score), 100) / 100)

    sub1, sub2 = st.columns(2)
    sub1.metric("Skill overlap", f"{match.skill_overlap_score}/100")
    sub2.metric("Text similarity", f"{match.text_similarity_score}/100")

    m1, m2 = st.columns(2)
    with m1:
        st.subheader("✅ Matched skills")
        st.write(", ".join(match.matched_skills) if match.matched_skills else "None detected.")
    with m2:
        st.subheader("❗ Missing from your resume")
        st.write(", ".join(match.missing_skills) if match.missing_skills else "None — great coverage!")

    st.subheader("💡 Suggestions")
    for tip in r["tips"]:
        st.markdown(f"- {tip}")

    if r["ai_text"]:
        st.subheader("🤖 AI-powered suggestions")
        st.write(r["ai_text"])
    elif not ai_api_key:
        st.info(
            "AI-powered suggestions aren't available right now (no API key "
            "configured for this app) — the rule-based suggestions above "
            "still apply."
        )

    st.divider()
    st.subheader("Download this report")
    d1, d2 = st.columns(2)
    with d1:
        docx_bytes = build_docx_report(
            r["resume_name"], r["jd_name"], match, verdict, r["tips"], r["ai_text"]
        )
        st.download_button(
            "⬇️ Download as Word (.docx)",
            data=docx_bytes,
            file_name="job_stitch_report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    with d2:
        pdf_bytes = build_pdf_report(
            r["resume_name"], r["jd_name"], match, verdict, r["tips"], r["ai_text"]
        )
        st.download_button(
            "⬇️ Download as PDF",
            data=pdf_bytes,
            file_name="job_stitch_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    if ai_api_key:
        st.divider()
        st.subheader("🔄 Update your resume for this job")
        st.write(
            "Rewrites your resume to better match this job description — "
            "reordering, rephrasing, and emphasizing your real experience "
            "with the JD's language. It won't invent new experience, "
            "employers, or dates."
        )
        update_clicked = st.button("Update as per requirement", use_container_width=True)
        if update_clicked:
            try:
                with st.spinner("Rewriting your resume for this job..."):
                    updated_text = generate_updated_resume(
                        r["resume_text"], r["jd_text"], match, ai_provider, ai_api_key
                    )
                    st.session_state["updated_resume_pdf"] = build_updated_resume_pdf(
                        updated_text
                    )
            except RuntimeError as exc:
                st.warning(str(exc))

        if "updated_resume_pdf" in st.session_state:
            st.success("Your updated resume is ready.")
            st.download_button(
                "⬇️ Download updated resume (.pdf)",
                data=st.session_state["updated_resume_pdf"],
                file_name="updated_resume.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        st.divider()
        st.subheader("🏢 Find similar organizations")
        st.write(
            "AI-brainstormed list of ~20 organizations likely to have "
            "similar roles, based on this job description — a starting "
            "point for your own research, not a live job search."
        )
        orgs_clicked = st.button("Find similar organizations", use_container_width=True)
        if orgs_clicked:
            try:
                with st.spinner("Brainstorming similar organizations..."):
                    st.session_state["similar_orgs_text"] = generate_similar_organizations(
                        r["jd_text"], ai_provider, ai_api_key
                    )
            except RuntimeError as exc:
                st.warning(str(exc))

        if "similar_orgs_text" in st.session_state:
            st.write(st.session_state["similar_orgs_text"])

st.divider()
st.caption(
    "Built with Streamlit + scikit-learn. Skill matching runs entirely "
    "locally and for free; AI tools are included at no cost to you."
)

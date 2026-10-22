"""
AI Resume Matcher — Streamlit app
==================================
Upload (or paste) a resume and a job description, get a fit score, see
which skills match and which are missing, get improvement suggestions,
and download the whole analysis as a Word or PDF report.

Run locally:    streamlit run app.py
Deploy free:    https://share.streamlit.io  (see README.md)
"""

import streamlit as st

from resume_matcher.exporting import build_docx_report, build_pdf_report
from resume_matcher.matching import compute_match
from resume_matcher.parsing import (
    UnsupportedFileTypeError,
    parse_pasted_text,
    parse_uploaded_file,
)
from resume_matcher.suggestions import (
    generate_ai_suggestions,
    generate_rule_based_suggestions,
    get_verdict,
)

st.set_page_config(page_title="AI Resume Matcher", page_icon="📄", layout="wide")


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


st.title("📄 AI Resume Matcher")
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

with st.expander("⚙️ Optional: enable AI-powered suggestions"):
    st.write(
        "The match score and suggestions above always work for free with "
        "no setup. If you'd like more natural-language, tailored rewrite "
        "suggestions (e.g. reworded bullet points), you can optionally "
        "provide your own API key below. **Your key is only used for this "
        "session and is never stored or logged.**"
    )
    ai_enabled = st.checkbox("Enable AI-powered suggestions")
    ai_provider, ai_api_key = None, None
    if ai_enabled:
        ai_provider = st.selectbox(
            "Provider",
            ["groq", "openai", "anthropic"],
            help=(
                "Groq is free (no credit card needed) and works well for this. "
                "OpenAI and Anthropic also work if you already have a paid key with them."
            ),
        )
        if ai_provider == "groq":
            st.caption(
                "Get a free key at [console.groq.com/keys](https://console.groq.com/keys) "
                "— just sign up, no credit card required."
            )
        ai_api_key = st.text_input(f"Your {ai_provider} API key", type="password")

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
            if ai_enabled:
                if not ai_api_key:
                    st.warning("AI mode is on but no API key was entered — showing free suggestions only.")
                else:
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
            "jd_name": jd_name,
            "match": match,
            "verdict": verdict,
            "tips": tips,
            "ai_text": ai_text,
        }

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
            file_name="resume_fit_report.docx",
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
            file_name="resume_fit_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

st.divider()
st.caption(
    "Built with Streamlit + scikit-learn. Skill matching runs entirely "
    "locally and for free; AI suggestions are optional and use your own API key."
)

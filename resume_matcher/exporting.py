"""
exporting.py
------------
Builds a downloadable "Job Stitch Report" -- match score, matched/missing
skills, and suggestions -- as either a .docx or a .pdf, returned as raw
bytes so Streamlit's download_button can serve them directly without
touching disk.
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from .matching import MatchResult
from .suggestions import VerdictBand


def _report_sections(
    resume_name: str,
    jd_name: str,
    match: MatchResult,
    verdict: VerdictBand,
    suggestions: list[str],
    ai_suggestions: str | None,
):
    """Shared content plan so DOCX and PDF stay in sync."""
    return {
        "title": "Job Stitch Report",
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "resume_name": resume_name,
        "jd_name": jd_name,
        "verdict": verdict,
        "match": match,
        "suggestions": suggestions,
        "ai_suggestions": ai_suggestions,
    }


def build_docx_report(
    resume_name: str,
    jd_name: str,
    match: MatchResult,
    verdict: VerdictBand,
    suggestions: list[str],
    ai_suggestions: str | None = None,
) -> bytes:
    doc = Document()

    title = doc.add_heading("Job Stitch Report", level=0)
    title.runs[0].font.color.rgb = RGBColor(0xC1, 0x3C, 0xFF)

    meta = doc.add_paragraph()
    meta.add_run(f"Resume: {resume_name}\n").italic = True
    meta.add_run(f"Job description: {jd_name}\n").italic = True
    meta.add_run(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}").italic = True

    doc.add_heading("Overall Match", level=1)
    score_p = doc.add_paragraph()
    score_run = score_p.add_run(f"{match.overall_score} / 100 — {verdict.label}")
    score_run.bold = True
    score_run.font.size = Pt(16)
    doc.add_paragraph(verdict.message)

    doc.add_paragraph(
        f"Skill overlap score: {match.skill_overlap_score}/100    "
        f"Text similarity score: {match.text_similarity_score}/100"
    )

    doc.add_heading("Matched Skills", level=1)
    doc.add_paragraph(
        ", ".join(match.matched_skills) if match.matched_skills else "None detected."
    )

    doc.add_heading("Skills in the JD but not your resume", level=1)
    doc.add_paragraph(
        ", ".join(match.missing_skills) if match.missing_skills else "None — great coverage!"
    )

    doc.add_heading("Suggestions", level=1)
    for tip in suggestions:
        doc.add_paragraph(tip, style="List Bullet")

    if ai_suggestions:
        doc.add_heading("AI-Powered Suggestions", level=1)
        for line in ai_suggestions.split("\n"):
            if line.strip():
                doc.add_paragraph(line.strip())

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def build_pdf_report(
    resume_name: str,
    jd_name: str,
    match: MatchResult,
    verdict: VerdictBand,
    suggestions: list[str],
    ai_suggestions: str | None = None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], textColor=colors.HexColor("#C13CFF")
    )
    heading_style = styles["Heading2"]
    body_style = styles["BodyText"]
    italic_style = ParagraphStyle("Italic", parent=body_style, fontName="Helvetica-Oblique")

    story = [
        Paragraph("Job Stitch Report", title_style),
        Spacer(1, 6),
        Paragraph(f"Resume: {resume_name}", italic_style),
        Paragraph(f"Job description: {jd_name}", italic_style),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", italic_style),
        Spacer(1, 14),
        Paragraph("Overall Match", heading_style),
        Paragraph(f"<b>{match.overall_score} / 100 — {verdict.label}</b>", body_style),
        Spacer(1, 4),
        Paragraph(verdict.message, body_style),
        Spacer(1, 4),
        Paragraph(
            f"Skill overlap score: {match.skill_overlap_score}/100 &nbsp;&nbsp; "
            f"Text similarity score: {match.text_similarity_score}/100",
            body_style,
        ),
        Spacer(1, 10),
        Paragraph("Matched Skills", heading_style),
        Paragraph(
            ", ".join(match.matched_skills) if match.matched_skills else "None detected.",
            body_style,
        ),
        Spacer(1, 10),
        Paragraph("Skills in the JD but not your resume", heading_style),
        Paragraph(
            ", ".join(match.missing_skills) if match.missing_skills else "None — great coverage!",
            body_style,
        ),
        Spacer(1, 10),
        Paragraph("Suggestions", heading_style),
        ListFlowable(
            [ListItem(Paragraph(tip, body_style)) for tip in suggestions],
            bulletType="bullet",
        ),
    ]

    if ai_suggestions:
        story.append(Spacer(1, 10))
        story.append(Paragraph("AI-Powered Suggestions", heading_style))
        for line in ai_suggestions.split("\n"):
            if line.strip():
                story.append(Paragraph(line.strip(), body_style))

    doc.build(story)
    return buffer.getvalue()


_HEADING_LINE = re.compile(r"^[A-Z][A-Z0-9 /&\-]{2,40}$")


def build_updated_resume_pdf(resume_text: str, candidate_name: str = "") -> bytes:
    """
    Formats an AI-tailored resume (plain text, ALL CAPS section headers on
    their own line, '-' bullet points -- see
    suggestions._RESUME_REWRITE_SYSTEM_PROMPT for the exact contract) as a
    clean, standard black-on-white PDF meant to actually be submitted to an
    employer. Deliberately NOT styled with the app's purple/dark branding --
    a resume you send to a recruiter should look like a normal resume.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    name_style = ParagraphStyle(
        "CandidateName",
        parent=styles["Title"],
        textColor=colors.black,
        fontSize=18,
        spaceAfter=2,
    )
    heading_style = ParagraphStyle(
        "ResumeHeading",
        parent=styles["Heading2"],
        textColor=colors.black,
        fontSize=12,
        spaceBefore=10,
        spaceAfter=4,
        borderWidth=0,
        borderPadding=0,
    )
    body_style = ParagraphStyle(
        "ResumeBody", parent=styles["BodyText"], textColor=colors.black, fontSize=10
    )
    bullet_style = ParagraphStyle(
        "ResumeBullet",
        parent=body_style,
        leftIndent=14,
        bulletIndent=2,
    )

    story = []
    if candidate_name:
        story.append(Paragraph(escape(candidate_name), name_style))
        story.append(Spacer(1, 8))

    bullets: list[ListItem] = []

    def flush_bullets():
        if bullets:
            story.append(
                ListFlowable(list(bullets), bulletType="bullet", leftIndent=14)
            )
            bullets.clear()

    for raw_line in resume_text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("-", "•", "*")):
            bullets.append(
                ListItem(Paragraph(escape(line.lstrip("-•* ").strip()), bullet_style))
            )
            continue
        flush_bullets()
        if _HEADING_LINE.match(line):
            story.append(Paragraph(escape(line.title()), heading_style))
        else:
            story.append(Paragraph(escape(line), body_style))

    flush_bullets()

    doc.build(story)
    return buffer.getvalue()

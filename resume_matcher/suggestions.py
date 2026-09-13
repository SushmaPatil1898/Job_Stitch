"""
suggestions.py
--------------
Turns a MatchResult into human-readable advice.

`generate_rule_based_suggestions` always runs -- it's free, deterministic,
and needs no API key. `generate_ai_suggestions` is optional: if the user
pastes in their own OpenAI or Anthropic API key in the app, we send the
resume + JD + local analysis to the model for a more natural-language,
tailored rewrite suggestion. It's a thin wrapper so swapping providers
later is a one-function change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .matching import MatchResult

_SECTION_HEADERS = {
    "summary": ["summary", "objective", "profile"],
    "experience": ["experience", "employment", "work history"],
    "education": ["education", "academic"],
    "skills": ["skills", "technical skills", "core competencies"],
}

_ACHIEVEMENT_PATTERN = re.compile(
    r"\b\d+(\.\d+)?\s*%|\$\s?\d|\b\d+(\.\d+)?\s*(x|hours|days|weeks|months|"
    r"years|users|clients|projects|million|thousand|k)\b",
    re.IGNORECASE,
)


def _has_section(resume_text: str, keywords: list[str]) -> bool:
    lowered = resume_text.lower()
    return any(kw in lowered for kw in keywords)


@dataclass
class VerdictBand:
    label: str
    message: str


def get_verdict(overall_score: float) -> VerdictBand:
    if overall_score >= 75:
        return VerdictBand(
            "Strong match",
            "This resume is well aligned with the job description. A few "
            "small tweaks below could make it even stronger, but it's in "
            "good shape to submit.",
        )
    if overall_score >= 50:
        return VerdictBand(
            "Moderate match",
            "There's a reasonable overlap, but tailoring the resume before "
            "you submit it would meaningfully improve your chances.",
        )
    return VerdictBand(
        "Weak match",
        "This resume and job description don't overlap much yet. Consider "
        "whether this role is the right fit, and if so, plan for "
        "significant tailoring before submitting.",
    )


def generate_rule_based_suggestions(resume_text: str, match: MatchResult) -> list[str]:
    tips: list[str] = []

    if match.missing_skills:
        shown = ", ".join(match.missing_skills[:10])
        tips.append(
            f"The job description mentions these skills/keywords that "
            f"weren't found in your resume: {shown}. If you have genuine "
            f"experience with any of them, add them explicitly (recruiters "
            f"and ATS systems often filter on exact keyword matches)."
        )

    missing_sections = [
        name for name, kws in _SECTION_HEADERS.items()
        if not _has_section(resume_text, kws)
    ]
    if missing_sections:
        tips.append(
            f"Your resume doesn't appear to have a clearly labeled "
            f"{', '.join(missing_sections)} section. Adding clear headers "
            f"helps both recruiters and automated screening tools find "
            f"the information quickly."
        )

    if not _ACHIEVEMENT_PATTERN.search(resume_text):
        tips.append(
            "No quantified achievements (numbers, percentages, dollar "
            "amounts, team sizes, timeframes) were detected. Wherever "
            "possible, rewrite bullet points to show measurable impact, "
            "e.g. 'reduced processing time by 30%' rather than 'improved "
            "processing time'."
        )

    word_count = len(resume_text.split())
    if word_count < 150:
        tips.append(
            "Your resume text is quite short (~"
            f"{word_count} words). Make sure it fully reflects your "
            "experience -- an overly thin resume can undersell you even "
            "if you're a strong fit."
        )
    elif word_count > 1200:
        tips.append(
            "Your resume text is fairly long (~"
            f"{word_count} words), roughly more than 2 pages worth. "
            "Consider trimming to the most relevant experience for this "
            "specific role."
        )

    if match.resume_only_skills:
        shown = ", ".join(match.resume_only_skills[:8])
        tips.append(
            f"You list skills the JD doesn't mention ({shown}). These "
            f"aren't a problem, but if space is tight, prioritize the "
            f"skills the job actually asks for."
        )

    if not tips:
        tips.append(
            "No major gaps detected by the automated checks -- nice work. "
            "Do a final human read-through for tone, formatting, and typos "
            "before submitting."
        )

    return tips


_AI_SYSTEM_PROMPT = (
    "You are a career coach helping a candidate tailor their resume to a "
    "specific job description. Be specific and concrete, referencing "
    "actual content from the resume and JD where possible. Keep your "
    "response under 300 words, organized as short bullet points."
)


def _build_ai_prompt(resume_text: str, jd_text: str, match: MatchResult) -> str:
    return (
        f"RESUME:\n{resume_text[:6000]}\n\n"
        f"JOB DESCRIPTION:\n{jd_text[:4000]}\n\n"
        f"AUTOMATED ANALYSIS:\n"
        f"- Overall match score: {match.overall_score}/100\n"
        f"- Matched skills: {', '.join(match.matched_skills) or 'none'}\n"
        f"- Missing skills the JD asks for: {', '.join(match.missing_skills) or 'none'}\n\n"
        "Give me specific, actionable suggestions to tailor this resume "
        "for this job. Where relevant, suggest exact rewritten bullet "
        "points, not just general advice."
    )


def generate_ai_suggestions(
    resume_text: str,
    jd_text: str,
    match: MatchResult,
    provider: str,
    api_key: str,
) -> str:
    """
    provider: "openai" or "anthropic"
    Raises RuntimeError with a friendly message on any failure (missing
    package, bad key, network issue) so the caller can display it cleanly.
    """
    prompt = _build_ai_prompt(resume_text, jd_text, match)

    if provider == "openai":
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The 'openai' package isn't installed. Run "
                "'pip install openai' to enable AI suggestions."
            ) from exc
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _AI_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=600,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:  # noqa: BLE001 - surface any API error plainly
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc

    elif provider == "anthropic":
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "The 'anthropic' package isn't installed. Run "
                "'pip install anthropic' to enable AI suggestions."
            ) from exc
        try:
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=600,
                system=_AI_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Anthropic request failed: {exc}") from exc

    else:
        raise RuntimeError(f"Unknown AI provider: {provider}")

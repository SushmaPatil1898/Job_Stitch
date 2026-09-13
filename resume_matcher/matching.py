"""
matching.py
-----------
The core "how well does this resume fit this job description" logic.
No external AI calls here on purpose -- this module is the free, always-on
path so the tool works instantly for anyone who opens the app.

Two signals are combined into one overall score:

1. Skill overlap: which known skills/keywords appear in the JD, and how
   many of those also appear in the resume.
2. Text similarity: a TF-IDF + cosine similarity score between the two
   documents as a whole, which captures overlap in phrasing/terminology
   beyond just the curated skill list.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_SKILLS_PATH = Path(__file__).parent / "data" / "skills.json"


def _load_skills() -> dict[str, list[str]]:
    with open(_SKILLS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_SKILLS_BY_CATEGORY = _load_skills()
_ALL_SKILLS = sorted(
    {skill.lower() for skills in _SKILLS_BY_CATEGORY.values() for skill in skills}
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _find_skills_in_text(text: str) -> set[str]:
    normalized = _normalize(text)
    found = set()
    for skill in _ALL_SKILLS:
        # Word-boundary match so "r" doesn't match inside "your", etc.
        pattern = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"
        if re.search(pattern, normalized):
            found.add(skill)
    return found


def _top_tfidf_keywords(text: str, top_n: int = 15) -> list[str]:
    """Pull out the most distinctive words/phrases in a JD, independent of
    the curated skills list -- useful for niche roles the dictionary
    doesn't cover."""
    vectorizer = TfidfVectorizer(
        stop_words="english", ngram_range=(1, 2), max_features=50
    )
    try:
        matrix = vectorizer.fit_transform([text])
    except ValueError:
        return []
    scores = matrix.toarray()[0]
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(zip(terms, scores), key=lambda t: t[1], reverse=True)
    return [term for term, score in ranked[:top_n] if score > 0]


@dataclass
class MatchResult:
    overall_score: float          # 0-100
    skill_overlap_score: float    # 0-100
    text_similarity_score: float  # 0-100
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    resume_only_skills: list[str] = field(default_factory=list)
    jd_top_keywords: list[str] = field(default_factory=list)


def compute_match(resume_text: str, jd_text: str) -> MatchResult:
    if not resume_text.strip() or not jd_text.strip():
        raise ValueError("Both resume text and job description text are required.")

    resume_skills = _find_skills_in_text(resume_text)
    jd_skills = _find_skills_in_text(jd_text)

    matched = sorted(resume_skills & jd_skills)
    missing = sorted(jd_skills - resume_skills)
    resume_only = sorted(resume_skills - jd_skills)

    skill_overlap_score = (
        100.0 * len(matched) / len(jd_skills) if jd_skills else 100.0
    )

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform([resume_text, jd_text])
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    text_similarity_score = round(float(similarity) * 100, 1)

    # Weighted blend: skill overlap is the more interpretable/actionable
    # signal, so it carries more weight than raw text similarity.
    overall_score = round(0.65 * skill_overlap_score + 0.35 * text_similarity_score, 1)

    return MatchResult(
        overall_score=overall_score,
        skill_overlap_score=round(skill_overlap_score, 1),
        text_similarity_score=text_similarity_score,
        matched_skills=matched,
        missing_skills=missing,
        resume_only_skills=resume_only,
        jd_top_keywords=_top_tfidf_keywords(jd_text),
    )

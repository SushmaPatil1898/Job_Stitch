# AI Resume Matcher

A Streamlit web app that compares a resume against a job description,
scores how well they match, highlights missing skills/keywords, suggests
improvements, and lets you download the analysis as a Word or PDF report.

Built as a hands-on Python project covering file parsing (PDF/DOCX), NLP
(TF-IDF + cosine similarity), optional LLM integration, document
generation (python-docx, reportlab), and a Streamlit UI.

## Features

- Upload a resume and job description as PDF, DOCX, or TXT — or just paste the text in
- Overall match score (0-100), blending skill-keyword overlap with TF-IDF text similarity
- List of matched skills and skills the JD wants that your resume is missing
- Rule-based improvement suggestions (missing sections, no quantified achievements, length, etc.) — always free, no setup
- Optional AI-powered suggestions using your own OpenAI or Anthropic API key, for tailored rewrite advice
- Download the full report as a `.docx` or `.pdf`

## Project structure

```
ai-resume-matcher/
├── app.py                      # Streamlit app (entry point)
├── resume_matcher/
│   ├── parsing.py              # PDF/DOCX/TXT -> plain text
│   ├── matching.py             # Skill extraction + TF-IDF similarity scoring
│   ├── suggestions.py          # Rule-based tips + optional AI suggestions
│   ├── exporting.py            # Builds the .docx / .pdf report
│   └── data/skills.json        # Curated skills dictionary used for matching
├── samples/                    # Example resume + JD to try the app with
├── requirements.txt
└── README.md
```

## Running it locally

```bash
git clone https://github.com/<your-username>/ai-resume-matcher.git
cd ai-resume-matcher
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

This opens the app in your browser at `http://localhost:8501`. Try it out
with the sample files in `samples/` first.

`requirements.txt` already includes the `openai` and `anthropic` packages
needed for the optional AI mode. You do **not** need an API key to use the
core matching and suggestions, though — that part is 100% free and runs
locally.

If you do want the AI-powered suggestions, the simplest free option is
**Groq**: sign up at [console.groq.com](https://console.groq.com) (no
credit card required), create an API key under "API Keys", then in the
app check "Enable AI-powered suggestions", pick **groq** as the provider,
and paste your key in. OpenAI and Anthropic keys work too if you already
have one, but both require a paid account.

## Sharing it with friends (free hosting)

The easiest way to let friends use this without installing anything:

1. Push this project to a GitHub repo (see below).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click "New app", pick your repo, branch `main`, and set the main file to `app.py`.
4. Deploy. Streamlit Community Cloud gives you a public URL like
   `https://your-app-name.streamlit.app` that anyone can open and use —
   including the optional AI mode, since each visitor enters their own key.

## Pushing to GitHub

```bash
# from inside the ai-resume-matcher folder
git add .
git commit -m "Initial commit: AI resume matcher"
git branch -M main
git remote add origin https://github.com/<your-username>/ai-resume-matcher.git
git push -u origin main
```

(Create the empty repo on GitHub first, without a README, so there's no
merge conflict on first push.)

## How the matching works

1. **Skill extraction** — both documents are scanned against a curated
   dictionary (`resume_matcher/data/skills.json`) covering programming
   languages, data/cloud tools, clinical/regulatory terms, soft skills,
   and more. Feel free to extend this list for your own field.
2. **Skill overlap score** — the percentage of JD skills that also show
   up in the resume.
3. **Text similarity score** — a TF-IDF vector + cosine similarity
   comparison of the full resume vs. full JD text, which catches overlap
   in phrasing beyond the fixed skill list.
4. **Overall score** — a weighted blend (65% skill overlap, 35% text
   similarity), since exact skill matches are the more actionable signal.

## Notes / possible extensions

- The skills dictionary in `resume_matcher/data/skills.json` is a plain
  JSON file — easy to edit or extend for a specific industry.
- `generate_ai_suggestions` in `suggestions.py` is written so adding a
  new provider (e.g. a different model) is a small, isolated change.
- Scanned/image-only PDFs won't extract text (no OCR is wired in) — for
  those, paste the text instead.

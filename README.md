# Job Stitch

*Align Your Potential.*

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
- AI-powered suggestions, powered by a built-in Groq key — visitors never need to find or paste in their own API key
- **Update as per requirement** — rewrites your resume to better match the job description (no fabricated experience) and gives you a clean, ready-to-send **PDF**
- **Find similar organizations** — an AI-brainstormed list of ~20 organizations likely to have similar roles, as a starting point for your own research
- Download the full analysis report as a `.docx` or `.pdf`

## Project structure

```
job-stitch/
├── app.py                      # Streamlit app (entry point)
├── resume_matcher/
│   ├── parsing.py              # PDF/DOCX/TXT -> plain text
│   ├── matching.py             # Skill extraction + TF-IDF similarity scoring
│   ├── suggestions.py          # Rule-based tips + optional AI suggestions
│   ├── exporting.py            # Builds the .docx / .pdf report
│   └── data/skills.json        # Curated skills dictionary used for matching
├── assets/
│   ├── logo.png                # Full logo lockup (icon + wordmark + tagline)
│   └── icon.png                # Icon-only crop, used as the browser favicon
├── .streamlit/config.toml      # Luminous purple-and-black theme matching the logo
├── samples/                    # Example resume + JD to try the app with
├── requirements.txt
└── README.md
```

## Running it locally

```bash
git clone https://github.com/<your-username>/job-stitch.git
cd job-stitch
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

This opens the app in your browser at `http://localhost:8501`. Try it out
with the sample files in `samples/` first.

`requirements.txt` already includes the `openai` package needed for the
AI-powered tools (Groq's API is OpenAI-compatible, so no separate SDK is
needed). The core match score and rule-based suggestions always work with
**no API key and no setup** — that part is 100% free and runs locally.

The AI-powered tools (tailored suggestions, "Update as per requirement",
and "Find similar organizations") use a Groq API key configured by
whoever runs the app — visitors never see a key field. To enable them
when you run this yourself:

1. Get a free key at [console.groq.com/keys](https://console.groq.com/keys)
   (no credit card required).
2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and
   paste your key in (that file is gitignored, so it's never committed).

Without that file, the app still runs fine — it just shows a small notice
that the AI tools are unavailable, and everything else works as normal.

## Sharing it with friends (free hosting)

The easiest way to let friends use this without installing anything:

1. Push this project to a GitHub repo (see below).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click "New app", pick your repo, branch `main`, and set the main file to `app.py`.
4. Before (or after) deploying, open the app's **Settings → Secrets** and paste in:
   ```toml
   GROQ_API_KEY = "your-groq-api-key-here"
   ```
   This is what powers the AI tools for every visitor — it's stored securely
   by Streamlit, never exposed in the code or to visitors.
5. Deploy. Streamlit Community Cloud gives you a public URL like
   `https://your-app-name.streamlit.app` that anyone can open and use,
   AI tools included, with nothing for them to set up.

Since everyone shares this one key, Groq's free-tier rate limits are
shared too — if a lot of people use the AI tools at the same moment, some
requests may briefly fail. The core match score and suggestions are
unaffected either way.

## Pushing to GitHub

```bash
# from inside the job-stitch folder
git add .
git commit -m "Initial commit: Job Stitch"
git branch -M main
git remote add origin https://github.com/<your-username>/job-stitch.git
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

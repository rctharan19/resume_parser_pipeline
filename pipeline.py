"""
Resume Parser Pipeline
======================
End-to-end pipeline that parses raw resume text, validates structured data,
scores candidates against a job requirement, and returns a hiring recommendation.
"""

import json
import time
import anthropic
from jsonschema import validate, ValidationError

# ── Anthropic client ────────────────────────────────────────────────────────
client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env


# ── Helpers ─────────────────────────────────────────────────────────────────
def call(messages, response_format=None):
    """Call the Claude API and return the raw Message object."""
    kwargs = dict(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=messages,
    )
    return client.messages.create(**kwargs)


def text_of(message):
    """Extract the first text block from a Claude Message."""
    for block in message.content:
        if block.type == "text":
            return block.text
    return ""


def safe_parse_json(raw: str) -> dict | None:
    """Strip markdown fences then parse JSON; return None on failure."""
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error: {e}")
        return None


def coerce_types(data: dict, schema: dict) -> dict:
    """
    Best-effort type coercion for top-level fields described by a JSON schema.
    Handles integer / array / null mismatches that LLMs sometimes produce.
    """
    props = schema.get("properties", {})
    for key, spec in props.items():
        if key not in data:
            continue
        val = data[key]
        expected = spec.get("type")

        # integer coercion
        if expected == "integer" and not isinstance(val, int):
            try:
                data[key] = int(val)
            except (TypeError, ValueError):
                data[key] = 0

        # array coercion — wrap a bare string in a list
        if expected == "array" and isinstance(val, str):
            data[key] = [v.strip() for v in val.split(",") if v.strip()]

        # null-or-string: leave as-is
    return data


# ── Resume schema ───────────────────────────────────────────────────────────
RESUME_SCHEMA = {
    "type": "object",
    "properties": {
        "full_name":          {"type": "string"},
        "email":              {"type": ["string", "null"]},
        "years_experience":   {"type": "integer", "minimum": 0},
        "current_role":       {"type": "string"},
        "technical_skills":   {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "education_level":    {
            "type": "string",
            "enum": ["high_school", "bachelor", "master", "phd", "other"]
        },
        "previous_companies": {"type": "array", "items": {"type": "string"}},
        "languages":          {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "full_name", "years_experience", "current_role",
        "technical_skills", "education_level",
    ],
}

# ── Job requirements ─────────────────────────────────────────────────────────
JOB_REQUIREMENTS = {
    "title":            "Senior Data Scientist",
    "min_experience":   4,
    "required_skills":  ["Python", "SQL", "Machine Learning"],
    "preferred_skills": ["PyTorch", "TensorFlow", "MLflow", "Spark"],
    "min_education":    "bachelor",
}

EDUCATION_RANK = {
    "high_school": 0,
    "bachelor":    1,
    "master":      2,
    "phd":         3,
    "other":       0,
}


# ── Core pipeline steps ──────────────────────────────────────────────────────
def parse_resume(resume_text: str) -> dict | None:
    """Step 1 & 2: Extract structured candidate data from raw resume text."""
    raw = text_of(call(
        messages=[
            {
                "role": "system",
                "content": "Parse resumes into structured JSON. Return only valid JSON — no markdown fences, no commentary.",
            },
            {
                "role": "user",
                "content": (
                    "Parse this resume and return JSON with exactly these fields:\n"
                    "  full_name: string\n"
                    "  email: string or null\n"
                    "  years_experience: integer (total years of work experience)\n"
                    "  current_role: string\n"
                    "  technical_skills: array of strings (programming languages, tools, frameworks)\n"
                    "  education_level: one of high_school / bachelor / master / phd / other\n"
                    "  previous_companies: array of company names\n"
                    "  languages: array of spoken languages\n\n"
                    f"Resume:\n{resume_text}"
                ),
            },
        ],
    ))

    # Step 2: parse → coerce → validate
    parsed = safe_parse_json(raw)
    if parsed is None:
        return None

    coerced = coerce_types(parsed, RESUME_SCHEMA)

    try:
        validate(instance=coerced, schema=RESUME_SCHEMA)
        return coerced
    except ValidationError as e:
        print(f"  ⚠️  Validation error: {e.message}")
        return None


def score_candidate(candidate: dict, requirements: dict) -> dict:
    """
    Step 4: Score a parsed candidate against job requirements.

    Scoring breakdown (100 pts total):
      - Experience : 0–30 pts
      - Required skills : 0–40 pts
      - Preferred skills : 0–20 pts
      - Education : 0–10 pts
    """
    skills_lower = [s.lower() for s in candidate.get("technical_skills", [])]

    # Experience score (0–30)
    exp       = candidate.get("years_experience", 0)
    exp_req   = requirements["min_experience"]
    exp_score = min(30, int((exp / max(exp_req, 1)) * 30))

    # Required skills score (0–40)
    req_skills  = requirements["required_skills"]
    req_matches = sum(1 for s in req_skills if s.lower() in skills_lower)
    req_score   = int((req_matches / len(req_skills)) * 40)

    # Preferred skills score (0–20)
    pref_skills  = requirements["preferred_skills"]
    pref_matches = sum(1 for s in pref_skills if s.lower() in skills_lower)
    pref_score   = int((pref_matches / len(pref_skills)) * 20)

    # Education score (0–10)
    edu_level = candidate.get("education_level", "other")
    min_edu   = requirements["min_education"]
    edu_score = 10 if EDUCATION_RANK.get(edu_level, 0) >= EDUCATION_RANK.get(min_edu, 0) else 0

    total = exp_score + req_score + pref_score + edu_score

    # Step 5: hiring recommendation
    if   total >= 80: recommendation = "STRONG HIRE"
    elif total >= 60: recommendation = "PROCEED TO INTERVIEW"
    elif total >= 40: recommendation = "MAYBE — NEEDS REVIEW"
    else:             recommendation = "NOT SUITABLE"

    return {
        "experience_score":  exp_score,
        "required_skills":   req_score,
        "preferred_skills":  pref_score,
        "education":         edu_score,
        "total":             total,
        "recommendation":    recommendation,
        "matched_required":  [s for s in req_skills  if s.lower() in skills_lower],
        "matched_preferred": [s for s in pref_skills if s.lower() in skills_lower],
    }


# ── Sample resumes ───────────────────────────────────────────────────────────
RESUMES = [
    """
    Meera Iyer | meera.iyer@email.com
    Senior Data Scientist at FinEdge Analytics — 6 years total experience.
    M.Sc. Computer Science, IIT Bombay.
    Skills: Python, SQL, TensorFlow, PyTorch, MLflow, Spark, scikit-learn, Tableau.
    Languages: English, Hindi, Tamil.
    Previous: Infosys (2 years), Wipro (1.5 years).
    """,
    """
    Arjun Sharma | arjun.s@mail.com
    Junior Developer, 1.5 years experience.
    B.E. IT, VIT Vellore.
    Skills: HTML, CSS, JavaScript, React.
    Previous company: WebCraft Solutions.
    Languages: English, Telugu.
    """,
    """
    Dr. Sunita Rao
    Lead ML Engineer at DeepTech Labs — 9 years experience.
    Ph.D. in Machine Learning, IISc Bangalore.
    Skills: Python, SQL, PyTorch, TensorFlow, Spark, MLflow, Kubernetes, R, Scala.
    Former researcher at Microsoft Research and Google Brain.
    Languages: English, Kannada.
    """,
]


# ── Entry point ──────────────────────────────────────────────────────────────
def run_pipeline(resumes: list[str], requirements: dict) -> None:
    """Run the full parse → score → recommend pipeline for each resume."""
    rec_icon = {
        "STRONG HIRE":          "🟢",
        "PROCEED TO INTERVIEW": "🔵",
        "MAYBE — NEEDS REVIEW": "🟡",
        "NOT SUITABLE":         "🔴",
    }

    print(f"\nJOB: {requirements['title']}")
    print(f"Required skills : {requirements['required_skills']}")
    print(f"Preferred skills: {requirements['preferred_skills']}")
    print("=" * 65)

    for i, resume_text in enumerate(resumes, 1):
        print(f"\n🔍 Candidate {i}")

        # Steps 1–3: parse & validate
        candidate = parse_resume(resume_text)
        if candidate is None:
            print("  ❌ Resume parsing failed — skipping.")
            continue

        # Steps 4–5: score & recommend
        scores = score_candidate(candidate, requirements)

        print(f"  Name       : {candidate['full_name']}")
        print(f"  Role       : {candidate['current_role']}")
        print(f"  Experience : {candidate['years_experience']} years")
        print(f"  Education  : {candidate['education_level']}")
        print(f"  Skills     : {', '.join(candidate['technical_skills'][:6])}"
              f"{'...' if len(candidate['technical_skills']) > 6 else ''}")
        print(f"  Score      : {scores['total']}/100  "
              f"(exp:{scores['experience_score']}  req:{scores['required_skills']}  "
              f"pref:{scores['preferred_skills']}  edu:{scores['education']})")
        print(f"  Decision   : {rec_icon.get(scores['recommendation'], '❓')} "
              f"{scores['recommendation']}")
        print(f"  Required ✓ : {scores['matched_required']}")
        print(f"  Preferred ✓: {scores['matched_preferred']}")

        time.sleep(0.5)   # polite rate-limiting

    print("\n" + "=" * 65)
    print("Pipeline complete.")


if __name__ == "__main__":
    run_pipeline(RESUMES, JOB_REQUIREMENTS)

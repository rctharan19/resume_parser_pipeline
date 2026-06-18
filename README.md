# 🧠 Resume Parser Pipeline

An end-to-end pipeline that reads raw, unstructured resume text, extracts structured candidate data using an LLM, validates it against a JSON schema, scores each candidate against a job's requirements, and returns a clear hiring recommendation — all in one script.

---

## ✨ What It Does

| Step | Description |
|------|-------------|
| **1. Ingest** | Accepts raw resume text (plain paragraphs, no special format needed) |
| **2. Extract** | Calls Claude to parse the text into a strict JSON structure |
| **3. Validate** | Coerces types and validates the output against a `jsonschema` schema |
| **4. Score** | Scores candidates on experience, required skills, preferred skills, and education |
| **5. Recommend** | Returns one of four hiring decisions with a colour-coded icon |

### Scoring Breakdown (100 pts total)

| Component | Max pts | Logic |
|-----------|---------|-------|
| Experience | 30 | Proportional to `min_experience`; capped at 30 |
| Required skills | 40 | Fraction of required skills matched |
| Preferred skills | 20 | Fraction of preferred skills matched |
| Education | 10 | Meets or exceeds minimum education level → 10, else 0 |

### Hiring Decisions

| Score | Decision |
|-------|----------|
| ≥ 80 | 🟢 STRONG HIRE |
| ≥ 60 | 🔵 PROCEED TO INTERVIEW |
| ≥ 40 | 🟡 MAYBE — NEEDS REVIEW |
| < 40 | 🔴 NOT SUITABLE |

---

## 🗂️ Project Structure

```
resume-pipeline/
├── pipeline.py        # Full pipeline — parse, validate, score, recommend
├── requirements.txt   # Python dependencies
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/resume_parser_pipeline.git
cd resume_parser_pipeline
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # macOS / Linux
set  ANTHROPIC_API_KEY=sk-ant-...       # Windows CMD
```

> Get a key at [console.anthropic.com](https://console.anthropic.com).

### 5. Run the pipeline

```bash
python pipeline.py
```

---

## 📋 Sample Output

```
JOB: Senior Data Scientist
Required skills : ['Python', 'SQL', 'Machine Learning']
Preferred skills: ['PyTorch', 'TensorFlow', 'MLflow', 'Spark']
=================================================================

🔍 Candidate 1
  Name       : Meera Iyer
  Role       : Senior Data Scientist
  Experience : 6 years
  Education  : master
  Skills     : Python, SQL, TensorFlow, PyTorch, MLflow, Spark...
  Score      : 95/100  (exp:30  req:40  pref:20  edu:10)
  Decision   : 🟢 STRONG HIRE
  Required ✓ : ['Python', 'SQL']
  Preferred ✓: ['PyTorch', 'TensorFlow', 'MLflow', 'Spark']

🔍 Candidate 2
  Name       : Arjun Sharma
  Role       : Junior Developer
  Experience : 1 years
  Education  : bachelor
  Skills     : HTML, CSS, JavaScript, React...
  Score      : 17/100  (exp:7  req:0  pref:0  edu:10)
  Decision   : 🔴 NOT SUITABLE
  Required ✓ : []
  Preferred ✓: []

🔍 Candidate 3
  Name       : Dr. Sunita Rao
  Role       : Lead ML Engineer
  Experience : 9 years
  Education  : phd
  Skills     : Python, SQL, PyTorch, TensorFlow, Spark, MLflow...
  Score      : 100/100  (exp:30  req:40  pref:20  edu:10)
  Decision   : 🟢 STRONG HIRE
  Required ✓ : ['Python', 'SQL']
  Preferred ✓: ['PyTorch', 'TensorFlow', 'MLflow', 'Spark']
```

---

## ⚙️ Customisation

### Change the job requirements

Edit the `JOB_REQUIREMENTS` dict in `pipeline.py`:

```python
JOB_REQUIREMENTS = {
    "title":            "ML Engineer",
    "min_experience":   3,
    "required_skills":  ["Python", "PyTorch", "Docker"],
    "preferred_skills": ["Kubernetes", "MLflow", "AWS"],
    "min_education":    "master",
}
```

### Add your own resumes

Append plain-text strings to the `RESUMES` list, or read them from files:

```python
with open("resume.txt") as f:
    RESUMES.append(f.read())
```

### Adjust scoring weights

The four score components are calculated in `score_candidate()`.  
Change the ceiling constants (`30`, `40`, `20`, `10`) as long as they still sum to 100.

---

## 🔑 Key Concepts Demonstrated

- **LLM-powered structured extraction** — prompting Claude to return strict JSON from free-form text
- **JSON Schema validation** — using `jsonschema` to catch and surface model errors
- **Type coercion** — gracefully handling minor type mismatches (e.g. integer-as-string)
- **Deterministic scoring** — rule-based scoring layer on top of non-deterministic AI output
- **Rate-limit courtesy** — `time.sleep(0.5)` between API calls

---

## 📄 License

MIT — feel free to adapt this for your own hiring tools or as a learning reference.

# Sahi Dawa AI: AI Prescription Transparency & Care Assistant

**Pak Angels GenAI Hackathon (Cohort 11 - Health Care Category)**

## 🚀 The Vision
Patients often lack clarity regarding their prescribed medications—wondering if they fit their diagnosis, if cheaper generic equivalents exist, or if they are experiencing irrational, repetitive antibiotic prescribing. **Sahi Dawa** brings immediate transparency and cost awareness to patients, enabling them to consult confidently with qualified medical professionals. 

*Disclaimer: Sahi Dawa is an educational transparency tool. It does not replace doctor consultations, prescribe, or substitute medication autonomously.*

## 🛠️ MVP Feature Set
- **Prescription Analysis:** Inputs for diagnosis, medicine name, and dosage.
- **RAG-Powered Explanations:** Medicine definitions anchored safely to a curated, DRAP-referenced data catalogue (~30-50 verified records) to prevent AI hallucinations.
- **Cost Transparency:** Brand-vs-generic pricing comparisons to surface affordable local alternatives.
- **Agentic Memory & Pattern Detection:** Analyzes visit history across sequential encounters to flag risks like antimicrobial resistance from repeated antibiotic use.
- **Shareable Summary:** Generates a structured Patient Health Summary report.

## 👥 Hackathon Team Members
- **Abdullah Aamir** (Lead)
- **Abdullah**
- **Faraz Ahmed Memon**
- **Esha Inam**
- **Absar Ahmed**
- **Afra Naz**

## 🧱 Backend (deterministic catalogue + history layer)

The `backend/` service implements the deterministic, non-AI part of the pipeline: CSV
catalogue loading, medicine identification, same-medicine (active ingredient + strength +
dosage form) matching, price comparison (including normalized unit pricing per
tablet/capsule/mL), patient encounter history (SQLite), and repeated-antibiotic pattern
detection. `data/medicines.csv` is the source of truth for all medicine facts. RAG/LLM
explanation is a separate layer, in progress, not implemented here.

### Setup
```bash
cd backend
pip install -r requirements.txt
```

### Run the API
```bash
cd backend
python -m uvicorn app.main:app --reload
```
Interactive docs at `http://127.0.0.1:8000/docs`.

### Run the tests
```bash
cd backend
pytest
```

### Endpoints
- `POST /prescription` — identify a medicine (name + optional dosage), and if found, return
  the verified record, same-medicine alternatives, a price comparison, and save the
  encounter to patient history (returning any newly triggered pattern flags). Never
  guesses: unmatched medicines return `NOT_FOUND`, non-unique matches return `AMBIGUOUS`
  with the candidate records.
- `GET /medicine/{medicine_id}` — verified catalogue record for a medicine_id, or 404.
- `GET /alternatives/{medicine_id}` — same-medicine records (same active ingredient,
  strength and dosage form as the given medicine_id -- brand and pack size may differ) and
  a price comparison, or 404.
- `GET /history/{patient_id}` — a patient's stored encounters and any detected discussion
  flags (e.g. repeated antibiotic prescriptions). An unknown patient_id returns an empty
  history, not an error.

### Price comparison basis
Alternatives only ever include records with the same active ingredient, strength and
dosage form as the matched medicine (a 500mg tablet is never compared against a 250mg
tablet or a syrup). Because pack sizes can still differ, `price_comparison` reports two
independent bases:
- **Pack price** (`lowest_pack_price`, `pack_price_difference`) — the total price for the
  pack as sold, always available whenever a price exists.
- **Unit price** (`lowest_unit_price`, `unit_price_difference`, `comparison_basis`) —
  price normalized per tablet/capsule or per mL, only populated when the pack quantity can
  be reliably parsed from `pack_size` for the items being compared. When it can't,
  `comparison_basis` is `"PACK_PRICE_ONLY"` and the unit fields stay `null`.

Missing prices are always `null`, never `0` or estimated. The backend performs all of this
arithmetic; the LLM layer only explains the already-computed numbers.

### AI explanation layer
`POST /prescription` also tries to generate a plain-language `explanation` via Groq
(`app/services/explanation.py`), grounded strictly in the already-computed data. This
requires a `GROQ_API_KEY` environment variable. **If it's missing or the call fails, the
endpoint still returns 200 with `explanation: null`** — the medicine record, alternatives,
pricing and pattern flags are real, verified data and are never withheld because the
optional AI layer is unavailable.

## 🖥️ Frontend (thin client)

`frontend-web/` is a small, dependency-free HTML/CSS/JS app implementing the four screens
from the frontend handoff spec: Prescription → Results → Explanation → Summary. It only
calls the API and displays what comes back — no medicine matching, price arithmetic, or
history storage happens in the browser.

By default, `app/main.py` serves this frontend directly from the FastAPI backend
(mounted at `/`), so running the backend is enough to use the whole app at
`http://127.0.0.1:8000/` — same origin, no CORS to configure.

There's also a legacy Gradio frontend at `frontend/app.py` (`pip install -r frontend/requirements.txt && python frontend/app.py`), kept for reference; it isn't part of the deployed app.

## 🚀 Running everything locally

```bash
cd backend
pip install -r requirements.txt
export GROQ_API_KEY=your_key_here   # optional -- omit to run without AI explanations
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/` for the app, `http://127.0.0.1:8000/docs` for the API docs.

## ☁️ Deployment

The repo ships a root `Dockerfile` that builds one image serving both the API and the
static frontend, plus a `render.yaml` blueprint for a one-click free deploy on
[Render](https://render.com):

1. Push this repo to GitHub.
2. On Render: **New → Blueprint**, point it at the repo (it picks up `render.yaml`).
3. Set the `GROQ_API_KEY` secret in the Render dashboard (see `.env.example`).
4. Deploy. Render builds the Dockerfile and gives you a public URL serving the full app.

Any other Docker-friendly host (Railway, Fly.io, a VPS) works the same way — build the
root `Dockerfile`, set `GROQ_API_KEY`, expose the container's port.

**Known limitation:** patient history is a local SQLite file (`data/sahi_dawa.db`). On
most free hosting tiers this resets on redeploy/restart since the filesystem isn't
persistent. Fine for a demo; for durability across restarts, attach a persistent disk or
move history to a hosted database.

### Pattern detection
Repeated antibiotic prescriptions (3+ in a patient's history, `medicine_category` resolved
live from the catalogue, never stored redundantly) raise a `REPEATED_ANTIBIOTIC` discussion
flag on `POST /prescription` and `GET /history/{patient_id}`. This is always a discussion
flag, never a diagnosis or an accusation.

## 🖥️ Frontend

`frontend/app.py` is a Gradio UI, calling the backend's real endpoints
(`/prescription`, `/history/{patient_id}`) — no logic is duplicated in the frontend. This
replaces the originally planned React/Next.js frontend, a Team Lead-approved stack change
made under hackathon time constraints.

```bash
cd frontend
pip install -r requirements.txt
python app.py
```
Requires the backend running separately at `http://127.0.0.1:8000`.

## 🧪 Data Pipeline (provenance)

`data/medicines.csv` (131 verified records) was built via a three-step pipeline in
`data-pipeline/`:

1. `scrape_drap.py` — Playwright scraper against the official DRAP Pharmaceutical Product
   Price Index (https://e.dra.gov.pk/public/price), searched by generic name and known
   brand names.
2. `clean_and_merge.py` — cleans raw scrape output, maps brand names to their correct
   active ingredient, deduplicates by registration number + pack size.
3. `trim_and_fix.py` — final dedupe pass, brand-name cleanup, and per-ingredient trimming
   to keep the catalogue lean while preserving real price spread.

Intermediate outputs from each stage are kept in `data-pipeline/` for auditability
(`medicines_v1_original_32records.csv` → `medicines_v2_364records_unfiltered.csv` →
`medicines_v3_final_131records.csv`, matching `data/medicines.csv`). All records are
`data_status: VERIFIED`, sourced directly from DRAP.

## 📄 Documentation

Full PRD and the locked pre-PRD proposal are in `docs/`:
- `docs/Sahi_Dawa_PRD.pdf`
- `docs/Sahi_Dawa_Locked_Proposal.pdf`

## 📌 Status

- ✅ Backend: catalogue, matching, pricing, patient history, pattern detection
- ✅ Frontend (Gradio, thin client over the real backend)
- ✅ Data catalogue (131 verified DRAP records) + full pipeline provenance
- 🔄 RAG/AI explanation layer, in progress (Faraz)
- 🔄 Patient Health Summary endpoint (`/summary/{patient_id}`), in progress

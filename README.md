# Sahi Dawa AI

## AI Prescription Transparency & Care Assistant

**Pak Angels GenAI Hackathon, Cohort 11 (Health Care Category)**

Sahi Dawa AI is a prescription transparency tool designed to help patients better understand prescribed medicines, compare verified local medicine prices, and identify repeated antibiotic prescribing patterns across patient encounters.

The application combines a deterministic medicine catalogue and patient history system with an optional AI explanation layer. The AI does not make medicine matches or calculate prices. Those decisions and calculations are handled by the backend using verified catalogue data.

> **Disclaimer:** Sahi Dawa AI is an educational transparency tool. It does not replace a qualified doctor, prescribe medicines, diagnose medical conditions, or autonomously recommend medication substitutions.

---

## 🚀 The Vision

Patients often have questions about the medicines they are prescribed:

* What medicine is this?
* Is the prescribed strength available in the verified catalogue?
* Are there other brands with the same active ingredient and strength?
* Is there a lower-cost equivalent?
* Has the patient received antibiotics repeatedly?
* What does the available medicine information mean in simple language?

Sahi Dawa AI provides a transparent answer by separating factual medicine data from AI-generated explanations.

The core principle is:

**Verified data first, AI explanation second.**

---

## ✨ MVP Features

### Prescription Analysis

Users enter:

* Patient ID
* Diagnosis
* Medicine name
* Optional dosage or strength

The backend then identifies the medicine using the verified catalogue.

The system never silently guesses.

It returns one of three states:

* `FOUND` when there is one matching medicine
* `AMBIGUOUS` when multiple catalogue records match
* `NOT_FOUND` when no verified record matches

### Verified Medicine Information

For a matched medicine, the application displays information from `data/medicines.csv`, including:

* Medicine name
* Active ingredient
* Strength
* Dosage form
* Pack size
* Price
* Registration number
* DRAP source
* Verification date
* Medicine category

The catalogue currently contains **131 verified medicine records**.

### Same-Medicine Alternatives

Alternatives are restricted to medicines with the same:

* Active ingredient
* Strength
* Dosage form

Brand name and pack size may differ.

This prevents incorrect comparisons such as comparing a 250mg tablet with a 500mg tablet or comparing a tablet with a syrup.

### Price Transparency

The backend calculates price comparisons before the AI explanation is generated.

Depending on the available pack information, the system can compare:

* Pack price
* Unit price per tablet
* Unit price per capsule
* Unit price per mL

Missing prices are represented as `null`. The system does not invent or estimate missing prices.

### Patient History

Prescription encounters are stored in SQLite and can be retrieved using the patient's ID.

The system supports:

* Encounter history
* Medicine history
* Diagnosis history
* Pattern flags
* Patient summary information

### Repeated Antibiotic Detection

The system checks patient history for repeated antibiotic prescriptions.

Three or more antibiotic encounters can trigger:

`REPEATED_ANTIBIOTIC`

This is a discussion flag only.

It is not a diagnosis, medical conclusion, or accusation.

### AI Explanation

The application optionally uses Groq to generate a plain-language explanation of the already-computed backend result.

The AI explanation is grounded in the actual response data, including:

* Matched medicine information
* Price information
* Alternatives
* Patient history information
* Pattern flags

The AI does not perform the medicine matching or price calculations.

If `GROQ_API_KEY` is missing or the AI request fails, the API continues to work normally and returns:

```json
"explanation": null
```

The verified medicine data, alternatives, pricing, and pattern detection are not dependent on the AI layer.

### Patient Summary

The application provides a patient summary containing:

* Patient ID
* Encounter count
* First and last encounter dates
* Diagnoses
* Medicines used
* Detected discussion flags

---

## 🏗️ Architecture

Sahi Dawa AI uses a simple one-service architecture.

```text
                    ┌─────────────────────┐
                    │    Browser / UI     │
                    │  frontend-web/      │
                    └──────────┬──────────┘
                               │
                               │ HTTP
                               ▼
                    ┌─────────────────────┐
                    │     FastAPI API     │
                    │    backend/app/     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       Medicine Catalogue   SQLite History   Groq AI
       data/medicines.csv   data/sahi_dawa.db  optional
              │                │                │
              └────────────────┴────────────────┘
                         API Response
                              │
                              ▼
                         Browser UI
```

The frontend is intentionally a thin client.

Matching, price calculations, history storage, pattern detection, and AI explanation are handled by the backend.

---

## 📁 Project Structure

```text
sahi-dawa-ai/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── services/
│   │   │   ├── explanation.py
│   │   │   └── ...
│   │   └── ...
│   ├── tests/
│   └── requirements.txt
│
├── frontend-web/
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
├── frontend/
│   ├── app.py
│   └── requirements.txt
│
├── data/
│   ├── medicines.csv
│   └── sahi_dawa.db
│
├── data-pipeline/
│   ├── scrape_drap.py
│   ├── clean_and_merge.py
│   ├── trim_and_fix.py
│   └── intermediate datasets
│
├── docs/
│   ├── Sahi_Dawa_PRD.pdf
│   └── Sahi_Dawa_Locked_Proposal.pdf
│
├── Dockerfile
├── render.yaml
├── .env.example
├── README.md
└── ...
```

---

## 🧱 Backend

The backend is built with **FastAPI**.

It handles:

* Medicine catalogue loading
* Medicine matching
* Ambiguity handling
* Medicine lookup
* Same-medicine alternatives
* Price comparison
* Patient history
* Pattern detection
* Patient summaries
* Optional Groq explanations
* Serving the frontend

The medicine catalogue is the source of truth for medicine facts.

---

## 🔎 Medicine Matching

The matching system is deterministic.

For a prescription such as:

```text
Medicine: Azitron
Dosage: 250mg
```

the backend searches the verified catalogue.

If one record matches:

```text
FOUND
```

If multiple records match:

```text
AMBIGUOUS
```

The API returns the candidates so the user can select the correct record.

If nothing matches:

```text
NOT_FOUND
```

The system does not replace an unmatched medicine with a similar medicine.

For example, requesting:

```text
Azitron 500mg
```

does not automatically return:

```text
Azitron 250mg
```

---

## 💰 Price Comparison

The backend calculates pricing independently from the AI layer.

### Pack Price

The system can compare the total price of the medicine packs.

### Unit Price

When pack quantities can be reliably parsed, the system normalizes prices to:

* Price per tablet
* Price per capsule
* Price per mL

For example:

```text
Current medicine:
PKR 324.33 / 6 tablets
= PKR 54.05 per tablet
```

An alternative may have:

```text
PKR 225.10 / 6 tablets
= PKR 37.52 per tablet
```

The backend performs these calculations.

The AI only explains the already-computed results.

---

## 🤖 AI Explanation Layer

The optional AI explanation layer uses Groq.

The relevant service is:

```text
backend/app/services/explanation.py
```

The API sends the already-computed medicine and pricing information to the explanation layer.

The AI is not responsible for:

* Medicine identification
* Catalogue searching
* Price arithmetic
* Alternative selection
* Patient history storage
* Pattern detection

This separation keeps the critical application logic deterministic.

### Environment Variable

```bash
GROQ_API_KEY=your_key_here
```

The key should never be committed to GitHub.

For local development, use an environment variable or `.env` file.

For production, configure it as a secret in the hosting platform.

---

## 🌐 Frontend

The production frontend is located in:

```text
frontend-web/
```

It is a dependency-free HTML, CSS, and JavaScript application.

It implements four main screens:

```text
01 Prescription
02 Results
03 Explanation
04 Summary
```

The frontend does not contain medicine matching or pricing logic.

It simply:

```text
INPUT → API → RESPONSE → DISPLAY
```

The FastAPI application serves the frontend directly, so the entire application runs as one service.

### Production Frontend

The deployed application is available here:

[Sahi Dawa AI Live App](https://sahi-dawa.onrender.com?utm_source=chatgpt.com)

### API Documentation

Interactive Swagger documentation:

[Sahi Dawa AI API Docs](https://sahi-dawa.onrender.com/docs?utm_source=chatgpt.com)

---

## 🔌 API Endpoints

### Health Check

```http
GET /health
```

Checks whether the API is running.

### Prescription Analysis

```http
POST /prescription
```

Analyzes a prescription and returns:

* Match status
* Medicine information
* Candidates when ambiguous
* Alternatives
* Price comparison
* Pattern flags
* Patient history information
* Optional AI explanation

### Medicine Lookup

```http
GET /medicine/{medicine_id}
```

Returns a verified medicine record.

Returns `404` if the medicine ID does not exist.

### Medicine Alternatives

```http
GET /alternatives/{medicine_id}
```

Returns same-medicine alternatives and price comparison.

Returns `404` if the medicine ID does not exist.

### Patient History

```http
GET /history/{patient_id}
```

Returns stored encounters and discussion flags.

A patient with no previous encounters returns an empty history rather than an error.

### Patient Summary

```http
GET /summary/{patient_id}
```

Returns a structured summary of the patient's encounters and detected discussion flags.

---

## 🧪 Testing

The application was tested at both automated and live levels.

### Automated Tests

The backend test suite currently passes:

```text
53/53 tests passed
```

The tests cover the core backend functionality, including:

* Medicine matching
* `FOUND`
* `AMBIGUOUS`
* `NOT_FOUND`
* Medicine lookup
* Alternative lookup
* Price comparison
* Unit price calculation
* Patient history
* Repeated antibiotic detection
* Patient summaries
* AI explanation fallback
* API behavior

### Manual Production Testing

The deployed application was also tested manually against the live API and frontend.

Tested scenarios included:

| Test                            | Result |
| ------------------------------- | ------ |
| Application loads               | PASS   |
| Empty prescription validation   | PASS   |
| Azitron 250mg found             | PASS   |
| Groq explanation                | PASS   |
| Azeloc without dosage ambiguity | PASS   |
| Candidate selection             | PASS   |
| Nuberol-P 120mg/5ml ambiguity   | PASS   |
| Panadol not found               | PASS   |
| Azitron 500mg not found         | PASS   |
| Medicine endpoint               | PASS   |
| Invalid medicine endpoint       | PASS   |
| Alternatives endpoint           | PASS   |
| Invalid alternatives endpoint   | PASS   |
| New patient history             | PASS   |
| Repeated antibiotic detection   | PASS   |
| Patient summary                 | PASS   |

The production tests confirmed the three core matching states:

```text
FOUND
AMBIGUOUS
NOT_FOUND
```

They also confirmed that real Groq-generated explanations can be displayed through the frontend.

---

## 🗂️ Data Pipeline

The medicine catalogue is stored in:

```text
data/medicines.csv
```

It currently contains:

```text
131 verified records
```

The catalogue was built using a data pipeline under:

```text
data-pipeline/
```

### Step 1: DRAP Scraping

```text
scrape_drap.py
```

Uses the official DRAP Pharmaceutical Product Price Index as the source for medicine pricing information.

### Step 2: Cleaning and Merging

```text
clean_and_merge.py
```

Cleans the scraped data, maps brand names to active ingredients, and removes duplicate records.

### Step 3: Final Catalogue Cleanup

```text
trim_and_fix.py
```

Performs the final cleanup, deduplication, brand-name normalization, and catalogue trimming.

The resulting catalogue is:

```text
data/medicines.csv
```

Intermediate datasets are retained in `data-pipeline/` for traceability.

### Data Source

Official DRAP Pharmaceutical Product Price Index:

[DRAP Pharmaceutical Product Price Index](https://e.dra.gov.pk/public/price?utm_source=chatgpt.com)

---

## 💻 Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/abdullahaamir13/sahi-dawa-ai.git
cd sahi-dawa-ai
```

### 2. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Groq

Groq is optional.

Linux/macOS:

```bash
export GROQ_API_KEY=your_key_here
```

Windows PowerShell:

```powershell
$env:GROQ_API_KEY="your_key_here"
```

If you do not configure the key, the application still works. Only the AI explanation will be unavailable.

### 4. Start the application

From the `backend` directory:

```bash
python -m uvicorn app.main:app --reload
```

### 5. Open the application

Frontend:

```text
http://127.0.0.1:8000/
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 🧪 Running Tests Locally

From the project root:

```bash
cd backend
pytest
```

Expected result:

```text
53 passed
```

---

## 🐳 Docker

The repository includes a root-level `Dockerfile`.

Build the image:

```bash
docker build -t sahi-dawa-ai .
```

Run it:

```bash
docker run -p 8000:8000 -e GROQ_API_KEY=your_key_here sahi-dawa-ai
```

Then open:

```text
http://localhost:8000/
```

---

## ☁️ Deployment

The application is deployed using Render.

The repository includes:

```text
Dockerfile
render.yaml
```

The production architecture is a single service that serves both:

* FastAPI backend
* Static frontend

### Deployment Steps

1. Push the repository to GitHub.
2. Create a new Render Blueprint.
3. Connect the GitHub repository.
4. Render reads `render.yaml`.
5. Configure `GROQ_API_KEY` as a secret.
6. Deploy the service.
7. Open the generated public URL.

### Production Application

[Sahi Dawa AI on Render](https://sahi-dawa.onrender.com?utm_source=chatgpt.com)

### Production API Docs

[Swagger API Documentation](https://sahi-dawa.onrender.com/docs?utm_source=chatgpt.com)

### Render Free Tier Note

The current deployment uses a free hosting tier.

The service may sleep after inactivity, which can cause a cold start when the application is opened again.

Patient history is stored in a local SQLite database:

```text
data/sahi_dawa.db
```

On hosting environments without persistent storage, SQLite data may be lost after a restart or redeployment.

This is acceptable for the current hackathon/demo deployment.

For a production system, patient history should be moved to a persistent managed database or persistent storage.

---

## 🖥️ Legacy Gradio Frontend

The repository still contains the original Gradio frontend:

```text
frontend/app.py
```

It is retained for reference and historical compatibility.

It is **not the production frontend**.

The production application uses:

```text
frontend-web/
```

served directly by FastAPI.

---

## 📄 Documentation

Project documentation is available in:

```text
docs/
```

Including:

* `docs/Sahi_Dawa_PRD.pdf`
* `docs/Sahi_Dawa_Locked_Proposal.pdf`

---

## 👥 Hackathon Team

* **Abdullah Aamir** - Lead
* **Abdullah**
* **Faraz Ahmed Memon**
* **Esha Inam**
* **Absar Ahmed**
* **Afra Naz**

---

## 📊 Current Project Status

### Completed

* ✅ FastAPI backend
* ✅ Deterministic medicine matching
* ✅ `FOUND`, `AMBIGUOUS`, and `NOT_FOUND` states
* ✅ 131 verified medicine records
* ✅ DRAP data pipeline
* ✅ Same-medicine alternative matching
* ✅ Pack price comparison
* ✅ Unit price comparison
* ✅ SQLite patient history
* ✅ Repeated antibiotic detection
* ✅ Patient summary endpoint
* ✅ Groq AI explanation layer
* ✅ AI fallback when Groq is unavailable
* ✅ Production web frontend
* ✅ Backend/frontend integration
* ✅ CORS configuration
* ✅ Docker deployment
* ✅ Render deployment
* ✅ Swagger API documentation
* ✅ 53/53 automated tests passing
* ✅ Live production testing completed

### Known Limitations

* SQLite history is not persistent on the current free hosting setup.
* The Groq explanation layer depends on the availability of the configured Groq API.
* The current catalogue is a curated dataset and should not be treated as a complete national medicine database.
* AI explanations are informational and must not be treated as medical advice.

---

## 🔐 Safety and Transparency Principles

Sahi Dawa AI follows several important principles:

### No Silent Guessing

If the system cannot confidently identify a medicine, it does not substitute another medicine.

### Deterministic Core Logic

Medicine matching, alternative selection, price calculations, and pattern detection happen in the backend.

### AI as an Explanation Layer

The AI explains verified backend results rather than making the core medical-data decisions.

### Transparent Data

Medicine facts come from the verified catalogue and retain their source and verification information.

### Human Medical Oversight

The application is designed to support conversations between patients and qualified healthcare professionals, not replace them.

---

## 📌 Final Status

**Sahi Dawa AI is currently deployed and working as an end-to-end MVP.**

The system has:

```text
Verified Catalogue
        ↓
Deterministic Matching
        ↓
Price Transparency
        ↓
Patient History
        ↓
Pattern Detection
        ↓
Optional AI Explanation
        ↓
Web Interface
```

The project is ready for hackathon demonstration and MVP evaluation.

---

## 📜 License

This project was developed as part of the Pak Angels GenAI Hackathon.

See the repository for the applicable project and data usage details.

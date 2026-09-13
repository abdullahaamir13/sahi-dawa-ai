"""
Exercises the REAL FastAPI app against the REAL data/medicines.csv,
using the real matching/pricing/history/pattern-detection code paths.

Only the outbound Groq LLM call is stubbed (network to api.groq.com is not
reachable from this sandbox) -- everything else is the genuine app.
"""
import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.explanation import ExplanationService

results = []

def log(name, resp):
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    results.append({"case": name, "status_code": resp.status_code, "body": body})
    print(f"\n=== {name} -> HTTP {resp.status_code} ===")
    print(json.dumps(body, indent=2, default=str)[:1500])


with patch.object(ExplanationService, "explain", lambda self, *a, **k: "Stubbed explanation (real LLM call skipped in sandbox)."):
    with TestClient(app) as client:

        log("health", client.get("/health"))

        # 1. FOUND
        log("prescription: Azitron 250mg -> FOUND", client.post("/prescription", json={
            "patient_id": "PK-TEST-01", "diagnosis": "Throat infection",
            "medicine": "Azitron", "dosage": "250mg"
        }))

        # 2. AMBIGUOUS (pack size only differs)
        log("prescription: Azeloc (no dosage) -> AMBIGUOUS", client.post("/prescription", json={
            "patient_id": "PK-TEST-01", "diagnosis": "Throat infection",
            "medicine": "Azeloc"
        }))

        # 3. NOT_FOUND (not in catalogue)
        log("prescription: Panadol -> NOT_FOUND", client.post("/prescription", json={
            "patient_id": "PK-TEST-01", "diagnosis": "Fever",
            "medicine": "Panadol"
        }))

        # 4. NOT_FOUND (name matches, strength doesn't)
        log("prescription: Azitron 500mg -> NOT_FOUND (strength mismatch)", client.post("/prescription", json={
            "patient_id": "PK-TEST-01", "diagnosis": "Throat infection",
            "medicine": "Azitron", "dosage": "500mg"
        }))

        # 5. AMBIGUOUS across pack volumes (Nuberol-P)
        log("prescription: Nuberol-P 120mg/5ml -> AMBIGUOUS", client.post("/prescription", json={
            "patient_id": "PK-TEST-01", "diagnosis": "Fever",
            "medicine": "Nuberol-P", "dosage": "120mg/5ml"
        }))

        # 6. GET /medicine/{id} valid + invalid
        log("GET /medicine/MED011 (valid)", client.get("/medicine/MED011"))
        log("GET /medicine/MED999 (invalid -> 404)", client.get("/medicine/MED999"))

        # 7. GET /alternatives/{id} valid + invalid
        log("GET /alternatives/MED011 (valid)", client.get("/alternatives/MED011"))
        log("GET /alternatives/MED999 (invalid -> 404)", client.get("/alternatives/MED999"))

        # 8. Repeated antibiotic pattern: 3 antibiotic prescriptions, same patient
        pid = "PK-PATTERN-TEST"
        for med, dosage, diag in [
            ("Zetro", "250mg", "Chest infection"),
            ("Azitron", "250mg", "Sinus infection"),
            ("Savoxacin", "250mg", "UTI"),
        ]:
            r = client.post("/prescription", json={
                "patient_id": pid, "diagnosis": diag, "medicine": med, "dosage": dosage
            })
        log("3rd antibiotic Rx -> pattern_flags should include REPEATED_ANTIBIOTIC", r)

        # 9. GET /history for that patient
        log("GET /history/PK-PATTERN-TEST", client.get(f"/history/{pid}"))

        # 10. GET /history for a never-seen patient -> empty, 200
        log("GET /history/UNSEEN-PATIENT-XYZ -> empty, 200", client.get("/history/UNSEEN-PATIENT-XYZ"))

        # 11. GET /summary for the pattern-test patient
        log("GET /summary/PK-PATTERN-TEST", client.get(f"/summary/{pid}"))

        # 12. GET /summary for unseen patient -> empty summary
        log("GET /summary/UNSEEN-PATIENT-XYZ -> empty summary", client.get("/summary/UNSEEN-PATIENT-XYZ"))

with open("live_test_results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

print("\n\nSUMMARY:")
for r in results:
    print(f"  [{r['status_code']}] {r['case']}")

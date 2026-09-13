from app.models.schemas import NOT_FOUND_MESSAGE


def test_post_prescription_found(client):
    resp = client.post(
        "/prescription",
        json={
            "patient_id": "P001",
            "diagnosis": "Bacterial infection",
            "medicine": "BrandA",
            "dosage": "100mg",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "FOUND"
    assert body["medicine"]["medicine_id"] == "TESTX001"

    alt_ids = {a["medicine_id"] for a in body["alternatives"]}
    assert alt_ids == {"TESTX005", "TESTX006", "TESTX007"}

    comparison = body["price_comparison"]
    assert comparison["comparison_basis"] == "UNIT_PRICE"
    assert comparison["lowest_unit_price"] == 7.5
    assert comparison["lowest_unit_price_medicine_id"] == "TESTX005"
    assert comparison["lowest_pack_price"] == 90.0
    assert comparison["lowest_pack_price_medicine_id"] == "TESTX006"

    assert body["pattern_flags"] == []  # first encounter for this patient -> no flag yet


def test_post_prescription_not_found(client):
    resp = client.post(
        "/prescription",
        json={
            "patient_id": "P001",
            "diagnosis": "Bacterial infection",
            "medicine": "TotallyUnknownMedicine",
            "dosage": "500mg",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "NOT_FOUND"
    assert body["message"] == NOT_FOUND_MESSAGE
    assert body["medicine"] is None
    assert body["alternatives"] == []
    assert body["price_comparison"] is None


def test_post_prescription_ambiguous(client):
    resp = client.post(
        "/prescription",
        json={
            "patient_id": "P001",
            "diagnosis": "Bacterial infection",
            "medicine": "BrandA",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "AMBIGUOUS"
    assert body["medicine"] is None
    assert len(body["candidates"]) == 2


def test_get_medicine_success(client):
    resp = client.get("/medicine/TESTX001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["brand_name"] == "BrandA"
    assert body["medicine_category"] == "Antibiotic"


def test_get_medicine_not_found(client):
    resp = client.get("/medicine/DOES_NOT_EXIST")
    assert resp.status_code == 404
    assert resp.json()["detail"] == NOT_FOUND_MESSAGE


def test_get_alternatives_success(client):
    resp = client.get("/alternatives/TESTX001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_ingredient"] == "IngredientX"
    assert body["strength"] == "100mg"
    assert body["dosage_form"] == "Tablet"
    ids = {a["medicine_id"] for a in body["alternatives"]}
    assert ids == {"TESTX005", "TESTX006", "TESTX007"}
    assert body["price_comparison"]["lowest_unit_price"] == 7.5


def test_get_alternatives_not_found(client):
    resp = client.get("/alternatives/DOES_NOT_EXIST")
    assert resp.status_code == 404
    assert resp.json()["detail"] == NOT_FOUND_MESSAGE


def test_post_prescription_saves_encounter_and_flags_repeated_antibiotics(client):
    payload = {
        "patient_id": "P900",
        "diagnosis": "Bacterial infection",
        "medicine": "BrandA",
        "dosage": "100mg",
    }
    first = client.post("/prescription", json=payload).json()
    second = client.post("/prescription", json=payload).json()
    third = client.post("/prescription", json=payload).json()

    assert first["pattern_flags"] == []
    assert second["pattern_flags"] == []
    assert len(third["pattern_flags"]) == 1
    assert third["pattern_flags"][0]["flag_type"] == "REPEATED_ANTIBIOTIC"


def test_post_prescription_not_found_does_not_save_encounter(client):
    client.post(
        "/prescription",
        json={"patient_id": "P902", "diagnosis": "d", "medicine": "Unknown", "dosage": "1mg"},
    )
    resp = client.get("/history/P902")
    assert resp.json()["encounters"] == []


def test_get_history_returns_encounters_and_flags(client):
    payload = {
        "patient_id": "P901",
        "diagnosis": "Bacterial infection",
        "medicine": "BrandA",
        "dosage": "100mg",
    }
    for _ in range(3):
        client.post("/prescription", json=payload)

    resp = client.get("/history/P901")
    assert resp.status_code == 200
    body = resp.json()
    assert body["patient_id"] == "P901"
    assert len(body["encounters"]) == 3
    assert all(e["medicine_category"] == "Antibiotic" for e in body["encounters"])
    assert len(body["pattern_flags"]) == 1
    assert body["pattern_flags"][0]["flag_type"] == "REPEATED_ANTIBIOTIC"


def test_get_history_empty_for_unknown_patient(client):
    resp = client.get("/history/NOBODY")
    assert resp.status_code == 200
    body = resp.json()
    assert body["encounters"] == []
    assert body["pattern_flags"] == []

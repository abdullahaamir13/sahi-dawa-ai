from app.models.schemas import Encounter
from app.services.patterns import (
    REPEATED_ANTIBIOTIC_MESSAGE,
    detect_patterns,
    enrich_with_category,
)


def _encounter(encounter_id: int, category: str, medicine_id: str = "M1") -> Encounter:
    return Encounter(
        encounter_id=encounter_id,
        patient_id="P001",
        diagnosis="d",
        medicine_id=medicine_id,
        medicine_name="Med",
        medicine_category=category,
        dosage="10mg",
        encounter_date="2026-01-01",
    )


def test_three_antibiotic_encounters_raises_flag():
    # PRD Section 11 example: Amoxicillin, Panadol, Azithromycin, Amoxicillin -> 3 antibiotics
    encounters = [
        _encounter(1, "Antibiotic"),
        _encounter(2, "Non-antibiotic"),
        _encounter(3, "Antibiotic"),
        _encounter(4, "Antibiotic"),
    ]
    flags = detect_patterns(encounters)

    assert len(flags) == 1
    assert flags[0].flag_type == "REPEATED_ANTIBIOTIC"
    assert flags[0].message == REPEATED_ANTIBIOTIC_MESSAGE
    assert flags[0].safety_note == "This is a discussion flag, not a diagnosis."


def test_two_antibiotic_encounters_does_not_raise_flag():
    encounters = [
        _encounter(1, "Antibiotic"),
        _encounter(2, "Non-antibiotic"),
    ]
    assert detect_patterns(encounters) == []


def test_no_encounters_raises_no_flag():
    assert detect_patterns([]) == []


def test_enrich_with_category_reads_from_catalogue_at_read_time(sample_repository):
    raw = [
        {
            "encounter_id": 1,
            "patient_id": "P001",
            "diagnosis": "d",
            "medicine_id": "TESTX001",  # Antibiotic in the sample catalogue
            "medicine_name": "BrandA",
            "dosage": "100mg",
            "encounter_date": "2026-01-01",
        }
    ]
    enriched = enrich_with_category(sample_repository, raw)
    assert enriched[0].medicine_category == "Antibiotic"


def test_enrich_with_category_handles_unknown_medicine_id(sample_repository):
    """A medicine_id that no longer exists in the catalogue must not crash --
    history is never lost because a catalogue record was removed or renamed."""
    raw = [
        {
            "encounter_id": 1,
            "patient_id": "P001",
            "diagnosis": "d",
            "medicine_id": "DOES_NOT_EXIST",
            "medicine_name": "Ghost",
            "dosage": None,
            "encounter_date": "2026-01-01",
        }
    ]
    enriched = enrich_with_category(sample_repository, raw)
    assert enriched[0].medicine_category == "Unknown"

from app.models.schemas import MatchStatus, NOT_FOUND_MESSAGE
from app.services.matching import identify_medicine


def test_exact_brand_and_strength_match(sample_repository):
    result = identify_medicine(sample_repository, "BrandA", "100mg")
    assert result.status == MatchStatus.FOUND
    assert result.medicine.medicine_id == "TESTX001"


def test_case_and_whitespace_normalization(sample_repository):
    result = identify_medicine(sample_repository, "  branda  ", " 100MG ")
    assert result.status == MatchStatus.FOUND
    assert result.medicine.medicine_id == "TESTX001"


def test_generic_name_lookup(sample_repository):
    result = identify_medicine(sample_repository, "GenericY")
    assert result.status == MatchStatus.FOUND
    assert result.medicine.medicine_id == "TESTX004"


def test_brand_name_takes_precedence_and_disambiguates_by_strength(sample_repository):
    found_low = identify_medicine(sample_repository, "BrandA", "100mg")
    found_high = identify_medicine(sample_repository, "BrandA", "200mg")
    assert found_low.medicine.medicine_id == "TESTX001"
    assert found_high.medicine.medicine_id == "TESTX002"


def test_no_dosage_and_multiple_strengths_is_ambiguous(sample_repository):
    result = identify_medicine(sample_repository, "BrandA")
    assert result.status == MatchStatus.AMBIGUOUS
    assert result.medicine is None
    ids = {c.medicine_id for c in result.candidates}
    assert ids == {"TESTX001", "TESTX002"}


def test_generic_name_with_multiple_brands_at_same_strength_is_ambiguous(sample_repository):
    result = identify_medicine(sample_repository, "GenericX", "100mg")
    assert result.status == MatchStatus.AMBIGUOUS
    ids = {c.medicine_id for c in result.candidates}
    assert ids == {"TESTX001", "TESTX003", "TESTX005", "TESTX006", "TESTX007"}


def test_unknown_medicine_returns_standard_not_found_message(sample_repository):
    result = identify_medicine(sample_repository, "Nonexistentazole")
    assert result.status == MatchStatus.NOT_FOUND
    assert result.message == NOT_FOUND_MESSAGE
    assert result.medicine is None
    assert result.candidates == []


def test_unavailable_strength_for_known_name_is_not_found_not_a_guess(sample_repository):
    result = identify_medicine(sample_repository, "BrandA", "999mg")
    assert result.status == MatchStatus.NOT_FOUND
    assert result.message == NOT_FOUND_MESSAGE

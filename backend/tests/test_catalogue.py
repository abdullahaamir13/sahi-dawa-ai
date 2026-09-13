import pytest

from app.services.catalogue import (
    CatalogueValidationError,
    load_catalogue_dataframe,
    normalize_text,
)


def test_csv_loads_successfully(sample_csv_path):
    df = load_catalogue_dataframe(sample_csv_path)
    assert len(df) == 9


def test_missing_required_column_is_rejected(sample_dataframe_factory):
    columns = [
        "medicine_id", "brand_name", "generic_name", "active_ingredient", "strength",
        "dosage_form", "pack_size", "manufacturer", "price", "price_effective_date",
        "registration_number", "drap_source_url", "last_verified", "data_status",
        # medicine_category deliberately omitted
    ]
    rows = [["M1", "B", "G", "I", "10mg", "Tablet", "1's", "Manu", "1.0", "d", "r", "u", "v", "VERIFIED"]]
    path = sample_dataframe_factory(rows, columns)

    with pytest.raises(CatalogueValidationError):
        load_catalogue_dataframe(path)


def test_duplicate_medicine_id_is_rejected(sample_dataframe_factory):
    columns = [
        "medicine_id", "brand_name", "generic_name", "active_ingredient", "strength",
        "dosage_form", "pack_size", "manufacturer", "price", "price_effective_date",
        "registration_number", "drap_source_url", "last_verified", "data_status",
        "medicine_category",
    ]
    rows = [
        ["M1", "B", "G", "I", "10mg", "Tablet", "1's", "Manu", "1.0", "d", "r", "u", "v", "VERIFIED", "Antibiotic"],
        ["M1", "B2", "G2", "I2", "20mg", "Tablet", "1's", "Manu", "2.0", "d", "r", "u", "v", "VERIFIED", "Antibiotic"],
    ]
    path = sample_dataframe_factory(rows, columns)

    with pytest.raises(CatalogueValidationError):
        load_catalogue_dataframe(path)


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(CatalogueValidationError):
        load_catalogue_dataframe(tmp_path / "does_not_exist.csv")


def test_missing_price_becomes_none_not_zero(sample_repository):
    record = sample_repository.get_by_id("TESTX004")
    assert record.price is None


def test_normalize_text_handles_whitespace_and_case():
    assert normalize_text("  Brand A  ") == normalize_text("brand a")
    assert normalize_text("Brand   A") == normalize_text("brand a")

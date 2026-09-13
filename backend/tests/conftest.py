
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_catalogue_repository, get_history_repository
from app.main import app
from app.services.catalogue import CatalogueRepository
from app.services.history import HistoryRepository
from app.services.explanation import ExplanationService


SAMPLE_CSV_ROWS = [
    # medicine_id, brand_name, generic_name, active_ingredient, strength, dosage_form,
    # pack_size, manufacturer, price, price_effective_date, registration_number,
    # drap_source_url, last_verified, data_status, medicine_category
    ["TESTX001", "BrandA", "GenericX", "IngredientX", "100mg", "Tablet", "10's", "ManuA",
     "100.0", "01 Jan, 2026", "REG1", "http://example.com", "2026-01-01", "VERIFIED", "Antibiotic"],

    # different strength than TESTX001 -> must NOT be an alternative to it
    ["TESTX002", "BrandA", "GenericX", "IngredientX", "200mg", "Tablet", "10's", "ManuA",
     "150.0", "01 Jan, 2026", "REG2", "http://example.com", "2026-01-01", "VERIFIED", "Antibiotic"],

    # same strength but different dosage form than TESTX001 -> must NOT be an alternative to it
    ["TESTX003", "BrandB", "GenericX", "IngredientX", "100mg", "Capsule", "10's", "ManuB",
     "80.0", "01 Jan, 2026", "REG3", "http://example.com", "2026-01-01", "VERIFIED", "Antibiotic"],

    # standalone medicine with a missing price
    ["TESTX004", "BrandC", "GenericY", "IngredientX", "50mg", "Tablet", "5's", "ManuC",
     "", "", "REG4", "http://example.com", "2026-01-01", "VERIFIED", "Antibiotic"],

    # same medicine as TESTX001 (ingredient+strength+form), bigger pack, cheaper per tablet
    ["TESTX005", "BrandD", "GenericX", "IngredientX", "100mg", "Tablet", "20's", "ManuD",
     "150.0", "01 Jan, 2026", "REG6", "http://example.com", "2026-01-01", "VERIFIED", "Antibiotic"],

    # same medicine as TESTX001, but an unparseable pack size (lowest total pack price)
    ["TESTX006", "BrandE", "GenericX", "IngredientX", "100mg", "Tablet", "Strip", "ManuE",
     "90.0", "01 Jan, 2026", "REG7", "http://example.com", "2026-01-01", "VERIFIED", "Antibiotic"],

    # same medicine as TESTX001, parseable pack size but missing price
    ["TESTX007", "BrandF", "GenericX", "IngredientX", "100mg", "Tablet", "10's", "ManuF",
     "", "", "REG8", "http://example.com", "2026-01-01", "VERIFIED", "Antibiotic"],

    # equivalent for TESTX004 (ingredient+strength+form match), with a real price
    ["TESTX008", "BrandG", "GenericW", "IngredientX", "50mg", "Tablet", "10's", "ManuG",
     "60.0", "01 Jan, 2026", "REG9", "http://example.com", "2026-01-01", "VERIFIED", "Antibiotic"],

    # different active ingredient entirely -> must never appear as an alternative to anything above
    ["TESTZ001", "BrandZ", "GenericZ", "IngredientZ", "10mg", "Tablet", "10's", "ManuZ",
     "50.0", "01 Jan, 2026", "REG5", "http://example.com", "2026-01-01", "VERIFIED", "Non-antibiotic"],
]


SAMPLE_COLUMNS = [
    "medicine_id", "brand_name", "generic_name", "active_ingredient", "strength",
    "dosage_form", "pack_size", "manufacturer", "price", "price_effective_date",
    "registration_number", "drap_source_url", "last_verified", "data_status",
    "medicine_category",
]


@pytest.fixture
def sample_csv_path(tmp_path):
    path = tmp_path / "medicines.csv"
    df = pd.DataFrame(SAMPLE_CSV_ROWS, columns=SAMPLE_COLUMNS)
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def sample_repository(sample_csv_path):
    return CatalogueRepository.from_csv(sample_csv_path)


@pytest.fixture
def sample_dataframe_factory(tmp_path):
    """Lets a test write an arbitrary/malformed CSV and load it."""

    def _make(rows, columns):
        path = tmp_path / "custom.csv"
        pd.DataFrame(rows, columns=columns).to_csv(path, index=False)
        return path

    return _make


@pytest.fixture
def history_repository(tmp_path):
    return HistoryRepository(db_path=tmp_path / "test_history.db")


@pytest.fixture
def client(sample_repository, history_repository):
    app.dependency_overrides[get_catalogue_repository] = lambda: sample_repository
    app.dependency_overrides[get_history_repository] = lambda: history_repository

    # Keep API tests independent from the real Groq API.
    original_explain = ExplanationService.explain
    ExplanationService.explain = lambda self, *args, **kwargs: "Test explanation"

    with TestClient(app) as test_client:
        yield test_client

    ExplanationService.explain = original_explain
    app.dependency_overrides.clear()

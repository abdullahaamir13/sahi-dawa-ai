"""CSV catalogue loading, schema validation and lookup.

The CSV is the single source of truth for medicine facts. Nothing here
fabricates, estimates or infers a value that isn't present in the file.
"""

from pathlib import Path
from typing import List, Optional

import pandas as pd

from app.models.schemas import AlternativeRecord, CandidateSummary, MedicineRecord

REQUIRED_COLUMNS = [
    "medicine_id",
    "brand_name",
    "generic_name",
    "active_ingredient",
    "strength",
    "dosage_form",
    "pack_size",
    "manufacturer",
    "price",
    "price_effective_date",
    "registration_number",
    "drap_source_url",
    "last_verified",
    "data_status",
    "medicine_category",
]


class CatalogueValidationError(Exception):
    """Raised when the catalogue CSV does not match the required schema."""


def normalize_text(value: object) -> str:
    """Collapse whitespace and casefold, for safe, formatting-only comparisons."""
    if value is None:
        return ""
    text = str(value).strip()
    text = " ".join(text.split())
    return text.casefold()


def _clean_optional_str(value: object) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text if text else None


def _clean_price(value: object) -> Optional[float]:
    """Return a float price, or None if missing/unparseable. Never zero, never estimated."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_catalogue_dataframe(csv_path: Path) -> pd.DataFrame:
    """Load and validate the catalogue CSV, raising on schema problems.

    Does not silently continue with a malformed catalogue: missing required
    columns, an empty file, or duplicate medicine_id values are all fatal.
    """
    if not csv_path.exists():
        raise CatalogueValidationError(f"Catalogue file not found: {csv_path}")

    df = pd.read_csv(csv_path, dtype=str, keep_default_na=True)

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise CatalogueValidationError(
            f"Catalogue is missing required columns: {missing_columns}"
        )

    if df.empty:
        raise CatalogueValidationError("Catalogue CSV contains no medicine records")

    duplicate_ids = df["medicine_id"][df["medicine_id"].duplicated()].tolist()
    if duplicate_ids:
        raise CatalogueValidationError(
            f"Catalogue contains duplicate medicine_id values: {duplicate_ids}"
        )

    df["price"] = df["price"].apply(_clean_price)

    df["_brand_name_norm"] = df["brand_name"].apply(normalize_text)
    df["_generic_name_norm"] = df["generic_name"].apply(normalize_text)
    df["_active_ingredient_norm"] = df["active_ingredient"].apply(normalize_text)
    df["_strength_norm"] = df["strength"].apply(normalize_text)
    df["_dosage_form_norm"] = df["dosage_form"].apply(normalize_text)

    return df


def _row_to_medicine_record(row: "pd.Series") -> MedicineRecord:
    return MedicineRecord(
        medicine_id=row["medicine_id"],
        brand_name=row["brand_name"],
        generic_name=row["generic_name"],
        active_ingredient=row["active_ingredient"],
        strength=row["strength"],
        dosage_form=row["dosage_form"],
        pack_size=row["pack_size"],
        manufacturer=row["manufacturer"],
        price=row["price"] if pd.notna(row["price"]) else None,
        price_effective_date=_clean_optional_str(row.get("price_effective_date")),
        registration_number=_clean_optional_str(row.get("registration_number")),
        drap_source_url=_clean_optional_str(row.get("drap_source_url")),
        last_verified=_clean_optional_str(row.get("last_verified")),
        data_status=row["data_status"],
        medicine_category=row["medicine_category"],
    )


def _row_to_candidate_summary(row: "pd.Series") -> CandidateSummary:
    return CandidateSummary(
        medicine_id=row["medicine_id"],
        brand_name=row["brand_name"],
        generic_name=row["generic_name"],
        strength=row["strength"],
        dosage_form=row["dosage_form"],
        pack_size=row["pack_size"],
        manufacturer=row["manufacturer"],
    )


def _row_to_alternative_record(row: "pd.Series") -> AlternativeRecord:
    return AlternativeRecord(
        medicine_id=row["medicine_id"],
        brand_name=row["brand_name"],
        generic_name=row["generic_name"],
        strength=row["strength"],
        dosage_form=row["dosage_form"],
        pack_size=row["pack_size"],
        manufacturer=row["manufacturer"],
        price=row["price"] if pd.notna(row["price"]) else None,
        price_effective_date=_clean_optional_str(row.get("price_effective_date")),
        data_status=row["data_status"],
        last_verified=_clean_optional_str(row.get("last_verified")),
    )


class CatalogueRepository:
    """Deterministic read access over a loaded catalogue DataFrame."""

    def __init__(self, df: pd.DataFrame):
        self._df = df

    @classmethod
    def from_csv(cls, csv_path: Path) -> "CatalogueRepository":
        return cls(load_catalogue_dataframe(csv_path))

    def get_by_id(self, medicine_id: str) -> Optional[MedicineRecord]:
        matches = self._df[self._df["medicine_id"] == medicine_id]
        if matches.empty:
            return None
        return _row_to_medicine_record(matches.iloc[0])

    def find_by_name(self, name: str) -> pd.DataFrame:
        """Return catalogue rows matching brand_name, falling back to generic_name."""
        name_norm = normalize_text(name)
        if not name_norm:
            return self._df.iloc[0:0]

        brand_matches = self._df[self._df["_brand_name_norm"] == name_norm]
        if not brand_matches.empty:
            return brand_matches

        return self._df[self._df["_generic_name_norm"] == name_norm]

    def filter_by_strength(self, df: pd.DataFrame, strength: str) -> pd.DataFrame:
        strength_norm = normalize_text(strength)
        return df[df["_strength_norm"] == strength_norm]

    def find_equivalents(
        self,
        active_ingredient: str,
        strength: str,
        dosage_form: str,
        exclude_medicine_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """Records that are the same medicine: same active ingredient, same
        strength, same dosage form. Brand, manufacturer and pack size may
        differ -- that's the point of the comparison.
        """
        ai_norm = normalize_text(active_ingredient)
        strength_norm = normalize_text(strength)
        dosage_form_norm = normalize_text(dosage_form)

        matches = self._df[
            (self._df["_active_ingredient_norm"] == ai_norm)
            & (self._df["_strength_norm"] == strength_norm)
            & (self._df["_dosage_form_norm"] == dosage_form_norm)
        ]
        if exclude_medicine_id is not None:
            matches = matches[matches["medicine_id"] != exclude_medicine_id]
        return matches

    @staticmethod
    def to_medicine_record(row: "pd.Series") -> MedicineRecord:
        return _row_to_medicine_record(row)

    @staticmethod
    def to_candidate_summary(row: "pd.Series") -> CandidateSummary:
        return _row_to_candidate_summary(row)

    @staticmethod
    def to_alternative_record(row: "pd.Series") -> AlternativeRecord:
        return _row_to_alternative_record(row)

    def __len__(self) -> int:
        return len(self._df)


def default_catalogue_path() -> Path:
    """Path to data/medicines.csv, resolved relative to the repository root."""
    return Path(__file__).resolve().parents[3] / "data" / "medicines.csv"

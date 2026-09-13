"""Pydantic models for the deterministic catalogue/matching/pricing API."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

NOT_FOUND_MESSAGE = "This medicine is not currently available in our verified catalogue."

AMBIGUOUS_MESSAGE = (
    "Multiple verified catalogue records match this medicine name. "
    "Please specify the exact brand, strength or dosage form."
)

SAME_INGREDIENT_NOTE = (
    "These medicines share the same active ingredient, strength and dosage form "
    "according to our verified catalogue. This is not a recommendation to switch -- "
    "discuss any substitution with your doctor or pharmacist."
)


class MatchStatus(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"


class MedicineRecord(BaseModel):
    """A single verified catalogue record, as read from the CSV."""

    medicine_id: str
    brand_name: str
    generic_name: str
    active_ingredient: str
    strength: str
    dosage_form: str
    pack_size: str
    manufacturer: str
    price: Optional[float] = None
    price_effective_date: Optional[str] = None
    registration_number: Optional[str] = None
    drap_source_url: Optional[str] = None
    last_verified: Optional[str] = None
    data_status: str
    medicine_category: str


class CandidateSummary(BaseModel):
    """Minimal fields shown when a query matches more than one catalogue record."""

    medicine_id: str
    brand_name: str
    generic_name: str
    strength: str
    dosage_form: str
    pack_size: str
    manufacturer: str


class AlternativeRecord(BaseModel):
    """A same active-ingredient + strength + dosage-form catalogue record --
    i.e. the same medicine in a different brand and/or pack size, for
    comparison display. Not a different product, and not a recommendation.
    """

    medicine_id: str
    brand_name: str
    generic_name: str
    strength: str
    dosage_form: str
    pack_size: str
    manufacturer: str
    price: Optional[float] = None
    price_effective_date: Optional[str] = None
    data_status: str
    last_verified: Optional[str] = None
    pack_quantity: Optional[float] = None
    pack_unit: Optional[str] = None
    unit_price: Optional[float] = None


class PriceComparison(BaseModel):
    """Deterministic price comparison across a medicine and its equivalents.

    Two independent bases are reported: total pack price (always available
    whenever a price exists) and normalized unit price (only when pack
    quantity can be reliably parsed for every item being compared). The two
    can disagree -- a bigger pack can cost more in total but less per unit --
    so both are returned rather than collapsing to a single "cheapest".
    """

    current_price: Optional[float] = None
    current_pack_size: str
    current_pack_quantity: Optional[float] = None
    current_pack_unit: Optional[str] = None
    current_unit_price: Optional[float] = None

    lowest_pack_price: Optional[float] = None
    lowest_pack_price_medicine_id: Optional[str] = None
    lowest_pack_price_pack_size: Optional[str] = None
    pack_price_difference: Optional[float] = None

    lowest_unit_price: Optional[float] = None
    lowest_unit_price_medicine_id: Optional[str] = None
    lowest_unit_price_unit: Optional[str] = None
    unit_price_difference: Optional[float] = None

    comparison_basis: str = "PACK_PRICE_ONLY"
    note: str = SAME_INGREDIENT_NOTE


class AlternativesResponse(BaseModel):
    """Response for GET /alternatives/{id}."""

    medicine_id: str
    active_ingredient: str
    strength: str
    dosage_form: str
    alternatives: List[AlternativeRecord]
    price_comparison: PriceComparison
    note: str = SAME_INGREDIENT_NOTE


class Encounter(BaseModel):
    """A stored prescription encounter, with medicine_category resolved from
    the live catalogue at read time rather than copied at save time."""

    encounter_id: int
    patient_id: str
    diagnosis: str
    medicine_id: str
    medicine_name: str
    medicine_category: str
    dosage: Optional[str] = None
    encounter_date: str


class PatternFlag(BaseModel):
    """A discussion flag over a patient's history. Never a diagnosis."""

    flag_type: str
    message: str
    safety_note: str = "This is a discussion flag, not a diagnosis."


class HistoryResponse(BaseModel):
    """Response for GET /history/{patient_id}."""

    patient_id: str
    encounters: List[Encounter] = Field(default_factory=list)
    pattern_flags: List[PatternFlag] = Field(default_factory=list)



class SummaryMedication(BaseModel):
    """Medication record included in the patient health summary."""

    encounter_id: int
    medicine_id: str
    medicine_name: str
    medicine_category: str
    dosage_form: str
    dosage: Optional[str] = None
    encounter_date: str


class PatientHealthSummary(BaseModel):
    """Patient health summary generated from recorded prescription encounters."""

    patient_id: str
    total_encounters: int
    first_encounter_date: Optional[str] = None
    last_encounter_date: Optional[str] = None
    diagnoses_recorded: List[str] = Field(default_factory=list)
    medications_recorded: List[SummaryMedication] = Field(default_factory=list)
    pattern_flags: List[PatternFlag] = Field(default_factory=list)
    transparency_note: str    


class MedicineLookupResult(BaseModel):
    """Outcome of identifying a medicine name (+ optional dosage) in the catalogue."""

    status: MatchStatus
    message: Optional[str] = None
    medicine: Optional[MedicineRecord] = None
    candidates: List[CandidateSummary] = Field(default_factory=list)


class PrescriptionRequest(BaseModel):
    patient_id: str
    diagnosis: str
    medicine: str
    dosage: Optional[str] = None


class PrescriptionResponse(BaseModel):
    """Response for POST /prescription."""

    patient_id: str
    diagnosis: str
    medicine_query: str
    dosage_query: Optional[str] = None
    status: MatchStatus
    message: Optional[str] = None
    medicine: Optional[MedicineRecord] = None
    candidates: List[CandidateSummary] = Field(default_factory=list)
    alternatives: List[AlternativeRecord] = Field(default_factory=list)
    price_comparison: Optional[PriceComparison] = None
    pattern_flags: List[PatternFlag] = Field(default_factory=list)
    explanation: Optional[str] = None
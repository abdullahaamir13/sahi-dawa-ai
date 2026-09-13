"""Same-medicine matching and deterministic price comparison.

"Same medicine" means same active ingredient, same strength and same dosage
form -- a 500mg tablet is never treated as equivalent to a 250mg tablet or a
500mg syrup. All calculations are plain Python over catalogue values: no
estimation, no LLM involvement, no ranking beyond factual lowest-price and
lowest-unit-price computation.
"""

from typing import List, Optional, Tuple

from app.models.schemas import AlternativeRecord, MedicineRecord, PriceComparison
from app.services.catalogue import CatalogueRepository
from app.services.units import compute_unit_price, parse_pack_quantity


def get_equivalent_alternatives(
    repository: CatalogueRepository, medicine: MedicineRecord
) -> List[AlternativeRecord]:
    """Other catalogue records that are the same medicine: same active
    ingredient, strength and dosage form, excluding the medicine itself.
    Different brand and/or pack size only.
    """
    matches = repository.find_equivalents(
        active_ingredient=medicine.active_ingredient,
        strength=medicine.strength,
        dosage_form=medicine.dosage_form,
        exclude_medicine_id=medicine.medicine_id,
    )
    return [_to_priced_alternative(row) for _, row in matches.iterrows()]


def _to_priced_alternative(row) -> AlternativeRecord:
    record = CatalogueRepository.to_alternative_record(row)
    parsed = parse_pack_quantity(record.pack_size, record.dosage_form)
    if parsed is None:
        return record
    quantity, unit = parsed
    return record.model_copy(
        update={
            "pack_quantity": quantity,
            "pack_unit": unit,
            "unit_price": compute_unit_price(record.price, quantity),
        }
    )


def compare_prices(
    medicine: MedicineRecord, alternatives: List[AlternativeRecord]
) -> PriceComparison:
    """Compare a medicine against its equivalents on two independent bases.

    Pack-price basis: lowest total pack price, whenever a price exists.
    Unit-price basis: lowest normalized price-per-unit, only when the
    current medicine's own pack size is parseable AND at least one
    equivalent also has a parseable pack size in the same unit -- otherwise
    the unit fields stay null rather than comparing apples to oranges.
    Missing prices are never treated as zero and never estimated.
    """
    current_parsed = parse_pack_quantity(medicine.pack_size, medicine.dosage_form)
    current_pack_quantity, current_pack_unit = current_parsed if current_parsed else (None, None)
    current_unit_price = compute_unit_price(medicine.price, current_pack_quantity)

    # --- pack-price basis ---
    pack_candidates: List[Tuple[str, float, str]] = []
    if medicine.price is not None:
        pack_candidates.append((medicine.medicine_id, medicine.price, medicine.pack_size))
    for alt in alternatives:
        if alt.price is not None:
            pack_candidates.append((alt.medicine_id, alt.price, alt.pack_size))

    lowest_pack_id: Optional[str] = None
    lowest_pack_price: Optional[float] = None
    lowest_pack_pack_size: Optional[str] = None
    if pack_candidates:
        lowest_pack_id, lowest_pack_price, lowest_pack_pack_size = min(
            pack_candidates, key=lambda item: item[1]
        )

    pack_price_difference: Optional[float] = None
    if medicine.price is not None and lowest_pack_price is not None:
        pack_price_difference = round(medicine.price - lowest_pack_price, 2)

    # --- unit-price basis ---
    lowest_unit_id: Optional[str] = None
    lowest_unit_price: Optional[float] = None
    lowest_unit_unit: Optional[str] = None
    unit_price_difference: Optional[float] = None
    comparison_basis = "PACK_PRICE_ONLY"

    if current_unit_price is not None:
        unit_candidates: List[Tuple[str, float]] = [(medicine.medicine_id, current_unit_price)]
        for alt in alternatives:
            if alt.unit_price is not None and alt.pack_unit == current_pack_unit:
                unit_candidates.append((alt.medicine_id, alt.unit_price))

        if len(unit_candidates) > 1:
            lowest_unit_id, lowest_unit_price = min(unit_candidates, key=lambda item: item[1])
            lowest_unit_unit = current_pack_unit
            unit_price_difference = round(current_unit_price - lowest_unit_price, 2)
            comparison_basis = "UNIT_PRICE"

    return PriceComparison(
        current_price=medicine.price,
        current_pack_size=medicine.pack_size,
        current_pack_quantity=current_pack_quantity,
        current_pack_unit=current_pack_unit,
        current_unit_price=current_unit_price,
        lowest_pack_price=lowest_pack_price,
        lowest_pack_price_medicine_id=lowest_pack_id,
        lowest_pack_price_pack_size=lowest_pack_pack_size,
        pack_price_difference=pack_price_difference,
        lowest_unit_price=lowest_unit_price,
        lowest_unit_price_medicine_id=lowest_unit_id,
        lowest_unit_price_unit=lowest_unit_unit,
        unit_price_difference=unit_price_difference,
        comparison_basis=comparison_basis,
    )

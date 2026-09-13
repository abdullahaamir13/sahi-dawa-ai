"""Deterministic historical pattern detection.

Antibiotic status is resolved from the live catalogue via medicine_id at
read time -- never stored redundantly, never inferred by an LLM. Output is
always a discussion flag, never a diagnosis or an accusation.
"""

from typing import List

from app.models.schemas import Encounter, PatternFlag
from app.services.catalogue import CatalogueRepository

REPEATED_ANTIBIOTIC_THRESHOLD = 3

REPEATED_ANTIBIOTIC_MESSAGE = (
    "Your previous records show repeated antibiotic prescriptions. Please discuss "
    "whether continued antibiotic use is clinically necessary with your healthcare "
    "professional."
)


def enrich_with_category(
    catalogue: CatalogueRepository, raw_encounters: List[dict]
) -> List[Encounter]:
    """Attach medicine_category from the current catalogue to each stored encounter.

    A medicine_id no longer present in the catalogue resolves to "Unknown"
    rather than raising -- history is never lost because a catalogue record
    was removed or renamed.
    """
    enriched = []
    for row in raw_encounters:
        record = catalogue.get_by_id(row["medicine_id"])
        category = record.medicine_category if record else "Unknown"
        enriched.append(Encounter(**row, medicine_category=category))
    return enriched


def detect_patterns(encounters: List[Encounter]) -> List[PatternFlag]:
    """Flag discussion-worthy patterns in a patient's encounter history.

    Currently: repeated antibiotic prescriptions, by simple count across the
    full history (not limited to consecutive visits), matching the PRD
    Section 11 example.
    """
    antibiotic_count = sum(1 for e in encounters if e.medicine_category == "Antibiotic")

    flags: List[PatternFlag] = []
    if antibiotic_count >= REPEATED_ANTIBIOTIC_THRESHOLD:
        flags.append(
            PatternFlag(flag_type="REPEATED_ANTIBIOTIC", message=REPEATED_ANTIBIOTIC_MESSAGE)
        )
    return flags

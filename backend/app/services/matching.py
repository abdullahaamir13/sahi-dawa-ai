"""Deterministic medicine identification.

No LLM, no fuzzy/edit-distance matching. A query resolves only against
brand_name or generic_name (normalized for whitespace/case), optionally
narrowed by strength. Anything that doesn't resolve to exactly one record
comes back as NOT_FOUND or AMBIGUOUS -- never a guess.
"""

from typing import Optional

from app.models.schemas import (
    AMBIGUOUS_MESSAGE,
    NOT_FOUND_MESSAGE,
    MatchStatus,
    MedicineLookupResult,
)
from app.services.catalogue import CatalogueRepository


def identify_medicine(
    repository: CatalogueRepository, medicine_name: str, dosage: Optional[str] = None
) -> MedicineLookupResult:
    """Resolve a medicine name (+ optional dosage) to a unique catalogue record."""

    candidates = repository.find_by_name(medicine_name)

    if candidates.empty:
        return MedicineLookupResult(status=MatchStatus.NOT_FOUND, message=NOT_FOUND_MESSAGE)

    if dosage:
        strength_matches = repository.filter_by_strength(candidates, dosage)
        if strength_matches.empty:
            # The name matched, but not at the requested strength. Never fall
            # back to a different strength -- report as not found.
            return MedicineLookupResult(status=MatchStatus.NOT_FOUND, message=NOT_FOUND_MESSAGE)
        candidates = strength_matches

    if len(candidates) == 1:
        record = CatalogueRepository.to_medicine_record(candidates.iloc[0])
        return MedicineLookupResult(status=MatchStatus.FOUND, medicine=record)

    candidate_summaries = [
        CatalogueRepository.to_candidate_summary(row) for _, row in candidates.iterrows()
    ]
    return MedicineLookupResult(
        status=MatchStatus.AMBIGUOUS,
        message=AMBIGUOUS_MESSAGE,
        candidates=candidate_summaries,
    )

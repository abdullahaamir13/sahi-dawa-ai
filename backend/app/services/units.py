"""Deterministic pack-size parsing for unit-price normalization.

Only two unit types are ever inferred: tablet/capsule counts and mL for
liquids. Anything else -- vials, ambiguous strip counts, inhaler doses,
free-text pack descriptions -- is left unparsed rather than guessed, so the
caller falls back to comparing total pack price only.
"""

import re
from typing import Optional, Tuple

_COUNT_FORMS = {"tablet", "capsule"}

_ML_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*ml$")
_SINGLE_COUNT_RE = re.compile(r"^(\d+)\s*'?s?$")
_MULTIPLIED_COUNT_RE = re.compile(r"^(\d+)\s*x\s*(\d+)\s*'?s?$")


def parse_pack_quantity(pack_size: str, dosage_form: str) -> Optional[Tuple[float, str]]:
    """Return (quantity, unit) for a pack_size string, or None if not reliably parseable.

    unit is "ml" for anything expressed as a plain millilitre volume, or
    "tablet"/"capsule" when dosage_form is Tablet/Capsule and the pack_size
    is a plain or multiplied count (e.g. "10's", "1 x 10's", "2x7s").
    """
    if not pack_size:
        return None
    text = " ".join(str(pack_size).strip().casefold().split())

    ml_match = _ML_RE.match(text)
    if ml_match:
        return float(ml_match.group(1)), "ml"

    form = str(dosage_form).strip().casefold()
    if form in _COUNT_FORMS:
        multiplied = _MULTIPLIED_COUNT_RE.match(text)
        if multiplied:
            return float(int(multiplied.group(1)) * int(multiplied.group(2))), form

        single = _SINGLE_COUNT_RE.match(text)
        if single:
            return float(single.group(1)), form

    return None


def compute_unit_price(price: Optional[float], quantity: Optional[float]) -> Optional[float]:
    """price / quantity, or None if either input is missing/non-positive."""
    if price is None or quantity is None or quantity <= 0:
        return None
    return round(price / quantity, 2)

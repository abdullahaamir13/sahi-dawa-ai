from app.services.units import compute_unit_price, parse_pack_quantity


def test_parses_simple_tablet_count():
    assert parse_pack_quantity("10's", "Tablet") == (10.0, "tablet")
    assert parse_pack_quantity("14", "Capsule") == (14.0, "capsule")


def test_parses_multiplied_tablet_count():
    assert parse_pack_quantity("1 x 10's", "Tablet") == (10.0, "tablet")
    assert parse_pack_quantity("20x10", "Tablet") == (200.0, "tablet")
    assert parse_pack_quantity("2x7s", "Capsule") == (14.0, "capsule")


def test_parses_ml_liquid_pack_size_regardless_of_dosage_form():
    assert parse_pack_quantity("30ml", "Suspension") == (30.0, "ml")
    assert parse_pack_quantity("2.5 ml", "Other") == (2.5, "ml")
    assert parse_pack_quantity("2 ml", "Injection") == (2.0, "ml")


def test_case_and_whitespace_insensitive():
    assert parse_pack_quantity("  1 X 10'S  ", "Tablet") == (10.0, "tablet")


def test_unparseable_pack_size_returns_none():
    assert parse_pack_quantity("Vial", "Injection") is None
    assert parse_pack_quantity("Strip", "Tablet") is None
    assert parse_pack_quantity("200 doses", "Other") is None
    assert parse_pack_quantity("1's vial", "Injection") is None


def test_tablet_count_not_inferred_for_non_count_dosage_forms():
    # "10's" alone is ambiguous outside tablet/capsule -- don't guess a unit
    assert parse_pack_quantity("10's", "Injection") is None


def test_compute_unit_price_basic():
    assert compute_unit_price(100.0, 10.0) == 10.0
    assert compute_unit_price(150.0, 20.0) == 7.5


def test_compute_unit_price_handles_missing_or_invalid_inputs():
    assert compute_unit_price(None, 10.0) is None
    assert compute_unit_price(100.0, None) is None
    assert compute_unit_price(100.0, 0) is None

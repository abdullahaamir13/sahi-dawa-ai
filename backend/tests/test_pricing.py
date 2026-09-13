from app.services.pricing import compare_prices, get_equivalent_alternatives


def test_equivalent_alternatives_excludes_self_and_unrelated_ingredients(sample_repository):
    medicine = sample_repository.get_by_id("TESTX001")  # IngredientX, 100mg, Tablet
    alternatives = get_equivalent_alternatives(sample_repository, medicine)
    ids = {a.medicine_id for a in alternatives}

    assert "TESTX001" not in ids  # excludes itself
    assert ids == {"TESTX005", "TESTX006", "TESTX007"}
    assert "TESTZ001" not in ids  # different active ingredient must never appear


def test_different_strength_is_not_an_alternative(sample_repository):
    medicine = sample_repository.get_by_id("TESTX001")  # 100mg
    alternatives = get_equivalent_alternatives(sample_repository, medicine)
    ids = {a.medicine_id for a in alternatives}

    assert "TESTX002" not in ids  # same brand+ingredient, but 200mg


def test_different_dosage_form_is_not_an_alternative(sample_repository):
    medicine = sample_repository.get_by_id("TESTX001")  # Tablet
    alternatives = get_equivalent_alternatives(sample_repository, medicine)
    ids = {a.medicine_id for a in alternatives}

    assert "TESTX003" not in ids  # same ingredient+strength, but Capsule


def test_same_medicine_different_pack_size_is_comparable(sample_repository):
    medicine = sample_repository.get_by_id("TESTX001")  # pack_size "10's"
    alternatives = get_equivalent_alternatives(sample_repository, medicine)
    ids = {a.medicine_id for a in alternatives}

    assert "TESTX005" in ids  # same ingredient+strength+form, pack_size "20's"


def test_normalized_unit_price_calculation(sample_repository):
    medicine = sample_repository.get_by_id("TESTX001")  # 10's @ 100.0 -> 10.00/tablet
    alternatives = get_equivalent_alternatives(sample_repository, medicine)
    comparison = compare_prices(medicine, alternatives)

    assert comparison.current_pack_quantity == 10.0
    assert comparison.current_pack_unit == "tablet"
    assert comparison.current_unit_price == 10.0

    alt5 = next(a for a in alternatives if a.medicine_id == "TESTX005")  # 20's @ 150.0
    assert alt5.pack_quantity == 20.0
    assert alt5.pack_unit == "tablet"
    assert alt5.unit_price == 7.5  # 150.0 / 20

    assert comparison.comparison_basis == "UNIT_PRICE"
    assert comparison.lowest_unit_price == 7.5
    assert comparison.lowest_unit_price_medicine_id == "TESTX005"
    assert comparison.unit_price_difference == 2.5  # 10.00 - 7.50


def test_pack_price_lowest_can_differ_from_unit_price_lowest(sample_repository):
    """TESTX006 has the cheapest total pack price but an unparseable pack size,
    while TESTX005 has a higher total price but the cheapest price per tablet.
    Both bases must be reported rather than collapsed into one "cheapest".
    """
    medicine = sample_repository.get_by_id("TESTX001")
    alternatives = get_equivalent_alternatives(sample_repository, medicine)
    comparison = compare_prices(medicine, alternatives)

    assert comparison.lowest_pack_price == 90.0
    assert comparison.lowest_pack_price_medicine_id == "TESTX006"

    assert comparison.lowest_unit_price == 7.5
    assert comparison.lowest_unit_price_medicine_id == "TESTX005"


def test_missing_pack_quantity_gives_no_normalized_price(sample_repository):
    medicine = sample_repository.get_by_id("TESTX001")
    alternatives = get_equivalent_alternatives(sample_repository, medicine)
    alt6 = next(a for a in alternatives if a.medicine_id == "TESTX006")  # pack_size "Strip"

    assert alt6.pack_quantity is None
    assert alt6.pack_unit is None
    assert alt6.unit_price is None
    # the actual pack price is still shown even though unit price isn't available
    assert alt6.price == 90.0


def test_price_missing_never_assumed_zero(sample_repository):
    medicine = sample_repository.get_by_id("TESTX004")  # IngredientX, 50mg, Tablet, price missing
    alternatives = get_equivalent_alternatives(sample_repository, medicine)
    comparison = compare_prices(medicine, alternatives)

    assert comparison.current_price is None
    assert comparison.current_unit_price is None
    # TESTX008 (same ingredient+strength+form) has a real price and becomes the
    # lowest pack price -- the missing current price is never fabricated as 0
    assert comparison.lowest_pack_price == 60.0
    assert comparison.lowest_pack_price_medicine_id == "TESTX008"
    assert comparison.pack_price_difference is None  # can't diff against an unknown price


def test_pack_size_and_quantity_preserved_in_comparison(sample_repository):
    medicine = sample_repository.get_by_id("TESTX001")
    alternatives = get_equivalent_alternatives(sample_repository, medicine)
    comparison = compare_prices(medicine, alternatives)

    assert comparison.current_pack_size == "10's"
    assert all(a.pack_size for a in alternatives)
    alt5 = next(a for a in alternatives if a.medicine_id == "TESTX005")
    assert alt5.pack_size == "20's"


def test_medicine_category_comes_from_catalogue_field(sample_repository):
    antibiotic = sample_repository.get_by_id("TESTX001")
    non_antibiotic = sample_repository.get_by_id("TESTZ001")

    assert antibiotic.medicine_category == "Antibiotic"
    assert non_antibiotic.medicine_category == "Non-antibiotic"

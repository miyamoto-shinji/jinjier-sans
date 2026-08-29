from jinjer_sans.config import BRAND_PRIMARY_CHARS, MASTERS


def test_brand_character_contract():
    assert len(BRAND_PRIMARY_CHARS) == 26
    assert "".join(BRAND_PRIMARY_CHARS) == "aegijnr0123456789@&%+-/:.,"


def test_weight_mapping_contract():
    assert [(m.public_weight, m.inter_weight, m.noto_weight) for m in MASTERS] == [
        (100, 125, 100),
        (400, 400, 465),
        (700, 700, 800),
        (900, 775, 900),
    ]

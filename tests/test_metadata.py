from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from jinjer_sans.metadata import set_static_metadata, set_variable_metadata


def _font():
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder([".notdef"])
    pen = TTGlyphPen(None)
    builder.setupGlyf({".notdef": pen.glyph()})
    builder.setupHorizontalMetrics({".notdef": (500, 0)})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupCharacterMap({})
    builder.setupNameTable({"familyName": "Fixture", "styleName": "Regular"})
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    builder.setupPost()
    return builder.font


def test_static_metadata_contract():
    font = _font()
    set_static_metadata(font, 700, "Bold")
    assert font["OS/2"].usWeightClass == 700
    assert font["OS/2"].achVendID == "JNJR"
    assert font["name"].getName(1, 3, 1, 0x409).toUnicode() == "jinjer sans"
    assert font["name"].getName(6, 3, 1, 0x409).toUnicode() == "jinjerSans-Bold"


def test_variable_metadata_uses_collision_free_names():
    font = _font()
    set_variable_metadata(font)
    assert font["name"].getName(1, 3, 1, 0x409).toUnicode() == "jinjer sans"
    assert font["name"].getName(4, 3, 1, 0x409).toUnicode() == "jinjer sans Variable"
    assert font["name"].getName(6, 3, 1, 0x409).toUnicode() == "jinjerSans-VF"

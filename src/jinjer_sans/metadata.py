from __future__ import annotations

from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables.ttProgram import Program

from .config import FAMILY_NAME, POSTSCRIPT_PREFIX, VENDOR_ID, VERSION

COPYRIGHT = (
    "Copyright 2014-2021 Adobe, with Reserved Font Name 'Source'. "
    "Copyright 2016 The Inter Project Authors. "
    "Copyright 2026 jinjer Co., Ltd., with Reserved Font Name 'jinjer'."
)
LICENSE_TEXT = (
    "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
    "This license is available with a FAQ at https://openfontlicense.org"
)
DESCRIPTION = (
    "jinjer sans is an OFL-licensed brand typeface combining Inter-derived Latin "
    "with Noto Sans JP-derived Japanese and jinjer-designed signature glyphs."
)


def _replace_name(font: TTFont, name_id: int, value: str) -> None:
    table = font["name"]
    table.names = [record for record in table.names if record.nameID != name_id]
    table.setName(value, name_id, 3, 1, 0x409)


def _ensure_smart_dropout(font: TTFont) -> None:
    expected = bytes((0xB8, 0x01, 0xFF, 0x85, 0xB0, 0x04, 0x8D))
    if "prep" not in font:
        font["prep"] = newTable("prep")
        font["prep"].program = Program()
    current = bytes(font["prep"].program.getBytecode())
    if expected not in current:
        program = Program()
        program.fromBytecode(expected + current)
        font["prep"].program = program


def _set_common(font: TTFont, style: str, postscript: str, variable: bool) -> None:
    # The variable and static Regular files may coexist in Figma or a browser
    # test machine. Give the variable font unique full/PostScript names while
    # retaining the shared family and typographic-family names.
    full_name = f"{FAMILY_NAME} Variable" if variable else f"{FAMILY_NAME} {style}"
    unique = f"{VERSION};{VENDOR_ID};{postscript}"
    values = {
        0: COPYRIGHT,
        1: FAMILY_NAME,
        2: "Regular" if variable else style,
        3: unique,
        4: full_name,
        5: f"Version {VERSION}",
        6: postscript,
        7: "jinjer is a trademark of jinjer Co., Ltd.",
        8: "jinjer Co., Ltd.",
        9: "The Inter Project Authors; Adobe; jinjer Co., Ltd.",
        10: DESCRIPTION,
        11: "https://jinjer.co.jp/",
        13: LICENSE_TEXT,
        14: "https://openfontlicense.org/",
        16: FAMILY_NAME,
        17: "Regular" if variable else style,
    }
    if variable:
        values[25] = POSTSCRIPT_PREFIX
    for name_id, value in values.items():
        _replace_name(font, name_id, value)
    # Platform 1 records are obsolete and can make family enumeration differ
    # between current macOS, Windows, and browser font stacks.
    font["name"].names = [record for record in font["name"].names if record.platformID != 1]
    font["head"].fontRevision = 1.0
    font["OS/2"].achVendID = VENDOR_ID
    font["post"].italicAngle = 0
    _ensure_smart_dropout(font)


def set_static_metadata(font: TTFont, weight: int, style: str) -> None:
    _set_common(font, style, f"{POSTSCRIPT_PREFIX}-{style}", variable=False)
    font["OS/2"].usWeightClass = weight
    selection = font["OS/2"].fsSelection
    selection &= ~((1 << 0) | (1 << 5) | (1 << 6))
    if weight == 400:
        selection |= 1 << 6
    if weight == 700:
        selection |= 1 << 5
    font["OS/2"].fsSelection = selection
    font["head"].macStyle = 1 if weight == 700 else 0


def set_variable_metadata(font: TTFont) -> None:
    _set_common(font, "Regular", f"{POSTSCRIPT_PREFIX}-VF", variable=True)
    buildStatTable(
        font,
        [
            {
                "tag": "wght",
                "name": "Weight",
                "ordering": 0,
                "values": [
                    {"value": 100, "name": "Thin"},
                    {"value": 400, "name": "Regular", "flags": 0x2},
                    {"value": 700, "name": "Bold"},
                    {"value": 900, "name": "Black"},
                ],
            }
        ],
        macNames=False,
    )
    font["name"].names = [record for record in font["name"].names if record.platformID != 1]
    if "fvar" in font:
        for instance in font["fvar"].instances:
            if instance.coordinates.get("wght") == font["fvar"].axes[0].defaultValue:
                instance.subfamilyNameID = 2
                instance.postscriptNameID = 6
    font["OS/2"].usWeightClass = 400
    font["OS/2"].fsSelection = (font["OS/2"].fsSelection & ~((1 << 0) | (1 << 5))) | (1 << 6) | (1 << 8)
    font["head"].macStyle = 0

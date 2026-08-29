from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from .config import (
    BRAND_PRIMARY_CHARS,
    CORPUS,
    DESKTOP_DIR,
    FAMILY_NAME,
    MASTERS,
    POSTSCRIPT_PREFIX,
    VARIABLE_FILENAME,
    WEB_DIR,
)


def _name(font: TTFont, name_id: int) -> str | None:
    value = font["name"].getName(name_id, 3, 1, 0x409)
    return value.toUnicode() if value else None


def _run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def check_fonts() -> None:
    variable_path = DESKTOP_DIR / VARIABLE_FILENAME
    if not variable_path.is_file():
        raise RuntimeError(f"Missing build output: {variable_path}")
    variable = TTFont(variable_path)
    axes = variable["fvar"].axes
    assert len(axes) == 1 and axes[0].axisTag == "wght"
    assert (axes[0].minValue, axes[0].defaultValue, axes[0].maxValue) == (100, 400, 900)
    assert _name(variable, 1) == FAMILY_NAME
    assert _name(variable, 4) == f"{FAMILY_NAME} Variable"
    assert _name(variable, 6) == f"{POSTSCRIPT_PREFIX}-VF"
    cmap = variable.getBestCmap() or {}
    for text in CORPUS:
        missing = sorted({ord(character) for character in text if not character.isspace() and ord(character) not in cmap})
        if missing:
            raise AssertionError(f"Corpus coverage failure: {[f'U+{cp:04X}' for cp in missing]}")
    for character in BRAND_PRIMARY_CHARS:
        assert ord(character) in cmap

    for master in MASTERS:
        static_path = DESKTOP_DIR / f"jinjerSans-{master.style_name}.ttf"
        static = TTFont(static_path)
        assert "fvar" not in static
        assert static["OS/2"].usWeightClass == master.public_weight
        assert _name(static, 1) == FAMILY_NAME
        assert _name(static, 6) != _name(variable, 6)
        instance = instantiateVariableFont(
            variable,
            {"wght": master.public_weight},
            inplace=False,
            static=True,
        )
        for character in BRAND_PRIMARY_CHARS:
            name = cmap[ord(character)]
            assert static["hmtx"][name] == instance["hmtx"][name]
        instance.close()
        static.close()
    variable.close()


def check_webfonts() -> None:
    manifest_path = WEB_DIR / "manifest.json"
    if not manifest_path.is_file():
        print("Webfont outputs not present; skipping web coverage check.")
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["family"] == FAMILY_NAME
    assert manifest["subsetCount"] > 0
    assert manifest["defaultDelivery"]["passesTransferBudget"] is True
    assert manifest["defaultDelivery"]["corpusTransferBytes"] <= manifest["defaultDelivery"]["baselineBytes"]
    groups = [
        manifest["defaultDelivery"]["fonts"]["400"]["subsets"],
        manifest["defaultDelivery"]["fonts"]["700"]["subsets"],
        manifest["variableDelivery"]["subsets"],
    ]
    for entries in groups:
        assert len(entries) == manifest["subsetCount"]
        for entry in entries:
            assert (WEB_DIR / entry["path"]).is_file()


def external_checks() -> None:
    variable = DESKTOP_DIR / VARIABLE_FILENAME
    desktop_fonts = [variable, *(DESKTOP_DIR / f"jinjerSans-{master.style_name}.ttf" for master in MASTERS)]
    if shutil.which("ots-sanitize"):
        for font in desktop_fonts:
            _run(["ots-sanitize", str(font)])
    else:
        print("ots-sanitize not installed; skipped")
    if shutil.which("hb-shape"):
        for weight in (100, 250, 400, 550, 700, 800, 900):
            for text in CORPUS:
                result = subprocess.run(
                    ["hb-shape", f"--variations=wght={weight}", str(variable), text],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if ".notdef" in result.stdout:
                    raise RuntimeError(f"HarfBuzz emitted .notdef at wght={weight}: {text}")
        print("HarfBuzz shaping passed at 100/250/400/550/700/800/900")
    else:
        print("hb-shape not installed; skipped")
    if shutil.which("fontbakery"):
        _run(["fontbakery", "check-universal", "--succinct", str(variable)])
    else:
        print("fontbakery not installed; skipped")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate jinjer sans outputs")
    parser.add_argument("--external", action="store_true")
    args = parser.parse_args()
    check_fonts()
    check_webfonts()
    if args.external:
        external_checks()
    print("jinjer sans QA passed")


if __name__ == "__main__":
    main()

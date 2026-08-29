from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, InstanceDescriptor, SourceDescriptor
from fontTools.ttLib import TTFont
from fontTools.varLib import build as build_varfont
from fontTools.varLib.instancer import instantiateVariableFont

from .brand import apply_brand_glyphs
from .config import (
    DESKTOP_DIR,
    DIST_DIR,
    FAMILY_NAME,
    MASTER_DIR,
    MASTERS,
    POSTSCRIPT_PREFIX,
    PROJECT_ROOT,
    RELEASE_DIR,
    SPECIMEN_DIR,
    UPSTREAM_DIR,
    VARIABLE_FILENAME,
    VARIABLE_WOFF2_FILENAME,
    VERSION,
    WEB_DIR,
)
from .metadata import set_static_metadata, set_variable_metadata
from .upstream import fetch_upstream, sha256, verify_upstream
from .webfont import build_webfonts

LAYOUT_TABLES = ("BASE", "GDEF", "GPOS", "GSUB")


def _repair_mark_filtering_sets(font: TTFont) -> None:
    """Restore Inter mark sets dropped by the upstream merge.

    The merger preserves GPOS lookups with UseMarkFilteringSet but its merged
    GDEF can lose MarkGlyphSetsDef. OTS correctly rejects that dangling
    reference. Inter glyph names are the base names in every merged master, so
    its two coverage sets can be restored without remapping.
    """
    if "GDEF" not in font or "GPOS" not in font:
        return
    inter_path = UPSTREAM_DIR / "vendor" / "fonts" / "Inter-4.1" / "InterVariable.ttf"
    inter = TTFont(inter_path)
    try:
        mark_sets = getattr(inter["GDEF"].table, "MarkGlyphSetsDef", None)
        if mark_sets is None:
            raise RuntimeError("Pinned Inter source has no GDEF MarkGlyphSetsDef")
        font["GDEF"].table.Version = max(font["GDEF"].table.Version, 0x00010002)
        font["GDEF"].table.MarkGlyphSetsDef = copy.deepcopy(mark_sets)
        for coverage in font["GDEF"].table.MarkGlyphSetsDef.Coverage:
            coverage.glyphs.sort(key=font.getGlyphID)
    finally:
        inter.close()


def _import_upstream_font_builder():
    source = str(UPSTREAM_DIR / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    from font import build as upstream  # type: ignore

    upstream.INTER_VARIABLE_EDGE_WEIGHTS = {
        master.upstream_style: {
            "wght": master.inter_weight,
            "outputWeight": 800 if master.upstream_style == "ExtraBold" else master.public_weight,
        }
        for master in MASTERS
    }
    return upstream


def _master_path(weight: int) -> Path:
    return MASTER_DIR / f"{POSTSCRIPT_PREFIX}-{weight}.ttf"


def build_masters(force: bool = False) -> list[Path]:
    fetch_upstream()
    expected = [_master_path(master.public_weight) for master in MASTERS]
    if not force and all(path.is_file() for path in expected):
        # Layout normalization is cheap and may evolve independently from the
        # expensive upstream outline merge.
        for path in expected:
            cached = TTFont(path)
            _repair_mark_filtering_sets(cached)
            cached.save(path, reorderTables=False)
            cached.close()
        _assert_master_compatibility(expected)
        print("Brand masters already exist; layout normalization refreshed.")
        return expected
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    upstream = _import_upstream_font_builder()
    family = upstream.FAMILIES["normal"]
    for master in MASTERS:
        upstream_weight = 800 if master.upstream_style == "ExtraBold" else master.public_weight
        print(
            f"Building master {master.public_weight}: "
            f"Inter {master.inter_weight} + Noto {master.noto_weight}"
        )
        manifest = upstream.build_one(
            family,
            upstream_weight,
            master.upstream_style,
            master.noto_weight,
        )
        source = Path(manifest["font"] if "font" in manifest else upstream._final_ttf_path(family, master.upstream_style))
        if not source.is_file():
            source = Path(upstream._final_ttf_path(family, master.upstream_style))
        font = TTFont(source)
        _repair_mark_filtering_sets(font)
        result = apply_brand_glyphs(font, master.public_weight)
        set_static_metadata(font, master.public_weight, master.style_name)
        destination = _master_path(master.public_weight)
        font.save(destination, reorderTables=False)
        font.close()
        print(f"  {destination} ({result.transformed_glyphs} brand outlines)")
    _assert_master_compatibility(expected)
    return expected


def _glyph_signature(font: TTFont, name: str):
    glyph = font["glyf"][name]
    if glyph.isComposite():
        return ("composite", tuple(component.glyphName for component in glyph.components))
    return (
        "simple",
        glyph.numberOfContours,
        len(glyph.coordinates) if hasattr(glyph, "coordinates") else 0,
        tuple(glyph.endPtsOfContours) if hasattr(glyph, "endPtsOfContours") else (),
    )


def _assert_master_compatibility(paths: list[Path]) -> None:
    fonts = [TTFont(path, lazy=True) for path in paths]
    try:
        order = fonts[0].getGlyphOrder()
        if any(font.getGlyphOrder() != order for font in fonts[1:]):
            raise RuntimeError("Master glyph orders differ")
        for name in order:
            signatures = [_glyph_signature(font, name) for font in fonts]
            if any(signature != signatures[0] for signature in signatures[1:]):
                raise RuntimeError(f"Incompatible master glyph: {name}")
    finally:
        for font in fonts:
            font.close()


def _designspace(paths: list[Path]) -> DesignSpaceDocument:
    document = DesignSpaceDocument()
    axis = AxisDescriptor()
    axis.name = "Weight"
    axis.tag = "wght"
    axis.minimum = 100
    axis.default = 400
    axis.maximum = 900
    document.addAxis(axis)
    for master, path in zip(MASTERS, paths):
        source = SourceDescriptor()
        source.path = str(path.resolve())
        source.name = master.style_name
        source.familyName = FAMILY_NAME
        source.styleName = master.style_name
        source.location = {"Weight": master.public_weight}
        source.copyInfo = master.public_weight == 400
        source.copyLib = master.public_weight == 400
        source.copyFeatures = master.public_weight == 400
        document.addSource(source)
        instance = InstanceDescriptor()
        instance.name = master.style_name
        instance.familyName = FAMILY_NAME
        instance.styleName = master.style_name
        instance.postScriptFontName = f"{POSTSCRIPT_PREFIX}-{master.style_name}"
        instance.location = {"Weight": master.public_weight}
        document.addInstance(instance)
    return document


def _write_woff2(source: Path, destination: Path) -> None:
    font = TTFont(source)
    font.flavor = "woff2"
    font.save(destination, reorderTables=False)
    font.close()


def build_fonts(force_masters: bool = False) -> list[Path]:
    paths = build_masters(force=force_masters)
    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
    print("Building wght 100-900 variable font; this can take several minutes...")
    variable, _, _ = build_varfont(
        _designspace(paths),
        exclude=list(LAYOUT_TABLES),
        optimize=True,
    )
    # varLib removes excluded layout data from the returned master objects.
    # Re-open the untouched Regular source so its stable Inter/Noto shaping,
    # including Latin kerning, is retained across the whole weight axis.
    regular = TTFont(paths[1])
    try:
        for tag in LAYOUT_TABLES:
            if tag in regular:
                variable[tag] = copy.deepcopy(regular[tag])
    finally:
        regular.close()
    set_variable_metadata(variable)
    variable_path = DESKTOP_DIR / VARIABLE_FILENAME
    variable.save(variable_path, reorderTables=False)
    variable.close()

    outputs = [variable_path]
    for master in MASTERS:
        source = TTFont(variable_path)
        static = instantiateVariableFont(
            source,
            {"wght": master.public_weight},
            inplace=False,
            optimize=True,
            updateFontNames=False,
            static=True,
        )
        source.close()
        set_static_metadata(static, master.public_weight, master.style_name)
        output = DESKTOP_DIR / f"{POSTSCRIPT_PREFIX}-{master.style_name}.ttf"
        static.save(output, reorderTables=False)
        static.close()
        outputs.append(output)

    _write_woff2(variable_path, DESKTOP_DIR / VARIABLE_WOFF2_FILENAME)
    outputs.append(DESKTOP_DIR / VARIABLE_WOFF2_FILENAME)
    for document in ("OFL.txt", "CREDITS.md", "FONTLOG.md"):
        shutil.copy2(PROJECT_ROOT / document, DESKTOP_DIR / document)
    print(f"Desktop outputs: {DESKTOP_DIR}")
    return outputs


def _copy_specimen() -> None:
    if SPECIMEN_DIR.exists():
        shutil.rmtree(SPECIMEN_DIR)
    shutil.copytree(PROJECT_ROOT / "specimen", SPECIMEN_DIR)
    # Source specimen assets live under dist/ during local development.
    # Inside the release package, specimen/, web/, and desktop/ are siblings.
    specimen_html = SPECIMEN_DIR / "index.html"
    specimen_content = specimen_html.read_text(encoding="utf-8")
    replacements = {
        "../dist/web/jinjer-sans-variable.css": "../web/jinjer-sans-variable.css",
        "../dist/desktop/jinjerSans-VF.ttf": "../desktop/jinjerSans-VF.ttf",
    }
    for source, packaged in replacements.items():
        specimen_content = specimen_content.replace(source, packaged)
    specimen_html.write_text(specimen_content, encoding="utf-8")


def _hash_manifest(paths: list[Path]) -> list[dict]:
    return [
        {
            "path": str(path.relative_to(DIST_DIR)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(paths)
        if path.is_file()
    ]


def build_release() -> Path:
    if not (DESKTOP_DIR / VARIABLE_FILENAME).is_file() or not (WEB_DIR / "jinjer-sans.css").is_file():
        raise RuntimeError("Run the font and web build stages first")
    # Documentation may be updated after an expensive font build; always
    # refresh the packaged copies when assembling a release.
    for document in ("OFL.txt", "CREDITS.md", "FONTLOG.md"):
        shutil.copy2(PROJECT_ROOT / document, DESKTOP_DIR / document)
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir(parents=True)
    _copy_specimen()
    package_root = RELEASE_DIR / f"jinjer-sans-{VERSION}"
    shutil.copytree(DESKTOP_DIR, package_root / "desktop")
    shutil.copytree(WEB_DIR, package_root / "web")
    shutil.copytree(SPECIMEN_DIR, package_root / "specimen")
    shutil.copy2(PROJECT_ROOT / "docs" / "INSTALL.md", package_root / "INSTALL.md")
    files = [path for path in package_root.rglob("*") if path.is_file()]
    checksums = "".join(f"{sha256(path)}  {path.relative_to(package_root)}\n" for path in sorted(files))
    (package_root / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    archive = RELEASE_DIR / f"jinjer-sans-{VERSION}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for path in sorted(package_root.rglob("*")):
            if path.is_file():
                target.write(path, Path(package_root.name) / path.relative_to(package_root))
    manifest = {
        "family": FAMILY_NAME,
        "version": VERSION,
        "archive": archive.name,
        "archiveSha256": sha256(archive),
        "files": _hash_manifest([path for path in package_root.rglob("*") if path.is_file()]),
    }
    (RELEASE_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Release archive: {archive}")
    return archive


def clean(upstream: bool = False) -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if upstream and UPSTREAM_DIR.exists():
        shutil.rmtree(UPSTREAM_DIR)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build jinjer sans")
    parser.add_argument("stage", choices=("fetch", "masters", "font", "web", "release", "all", "clean"))
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--force", action="store_true", help="Rebuild cached brand masters")
    parser.add_argument("--upstream", action="store_true", help="Also remove the upstream cache with clean")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.stage == "fetch":
        fetch_upstream()
    elif args.stage == "masters":
        build_masters(force=args.force)
    elif args.stage == "font":
        build_fonts(force_masters=args.force)
    elif args.stage == "web":
        verify_upstream()
        build_webfonts(args.jobs)
    elif args.stage == "release":
        build_release()
    elif args.stage == "all":
        build_fonts(force_masters=args.force)
        build_webfonts(args.jobs)
        build_release()
    elif args.stage == "clean":
        clean(upstream=args.upstream)


if __name__ == "__main__":
    main()

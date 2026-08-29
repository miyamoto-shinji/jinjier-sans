from __future__ import annotations

import concurrent.futures
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

from .config import CORPUS, DESKTOP_DIR, FAMILY_NAME, POSTSCRIPT_PREFIX, UPSTREAM_DIR, VARIABLE_FILENAME, WEB_DIR


def _load_upstream_webfont_module():
    path = UPSTREAM_DIR / "src" / "webfont" / "build.py"
    spec = importlib.util.spec_from_file_location("jinjer_upstream_webfont", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load upstream webfont builder: {path}")
    module = importlib.util.module_from_spec(spec)
    # Match normal import semantics. dataclasses consults sys.modules while
    # the dynamically loaded module body is still being executed.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _font_face(relative: str, weight: str | int, unicode_range: str | None = None, variable: bool = False) -> str:
    lines = [
        "@font-face {",
        f'  font-family: "{FAMILY_NAME}";',
        "  font-style: normal;",
        f"  font-weight: {weight};",
        "  font-display: swap;",
        f'  src: url("{relative}") format("{"woff2-variations" if variable else "woff2"}");',
    ]
    if unicode_range:
        lines.append(f"  unicode-range: {unicode_range};")
    lines.append("}")
    return "\n".join(lines)


def _entry(index: int, output: Path, item: object, upstream: object, relative: str) -> dict:
    return {
        "index": index,
        "path": relative,
        "bytes": output.stat().st_size,
        "sha256": _digest(output),
        "unicodeRange": upstream.format_unicode_range(item.codepoints),
        "codepointCount": len(item.codepoints),
    }


def _corpus_transfer(entries: list[dict], plan: list[object]) -> int:
    wanted = {ord(character) for text in CORPUS for character in text}
    return sum(entry["bytes"] for entry, item in zip(entries, plan) if wanted.intersection(item.codepoints))


def _promote_ui_core(plan: list[object], upstream: object) -> list[object]:
    """Put product-corpus codepoints in one non-overlapping first slice.

    Google Japanese slices distribute common UI characters across many files.
    A jinjer-specific core prevents a representative product screen from
    downloading the per-file OpenType overhead 15-20 times for both weights.
    """
    supported = set().union(*(set(item.codepoints) for item in plan))
    core = {ord(character) for text in CORPUS for character in text} & supported
    promoted = [
        upstream.WebFontSubset(
            name="jinjer-ui-core",
            codepoints=tuple(sorted(core)),
            note="jinjer product UI evaluation corpus",
        )
    ]
    for item in plan:
        remaining = tuple(sorted(set(item.codepoints) - core))
        if remaining:
            promoted.append(
                upstream.WebFontSubset(name=item.name, codepoints=remaining, note=item.note)
            )
    return promoted


def build_webfonts(jobs: int = 4) -> dict:
    source = DESKTOP_DIR / VARIABLE_FILENAME
    if not source.is_file():
        raise RuntimeError(f"Build the desktop font first: {source}")
    if WEB_DIR.exists():
        shutil.rmtree(WEB_DIR)
    for variant in ("400", "700", "vf"):
        (WEB_DIR / "w" / variant).mkdir(parents=True)
    (WEB_DIR / "nam").mkdir(parents=True)

    upstream = _load_upstream_webfont_module()
    with TTFont(source) as font:
        codepoints = set((font.getBestCmap() or {}).keys())
    slice_path = UPSTREAM_DIR / "vendor" / "nam-files" / "slices" / "japanese_default.txt"
    plan = upstream.build_google_japanese_subset_plan(codepoints, slice_path=slice_path)
    plan = _promote_ui_core(plan, upstream)

    sources = {
        "400": DESKTOP_DIR / f"{POSTSCRIPT_PREFIX}-Regular.ttf",
        "700": DESKTOP_DIR / f"{POSTSCRIPT_PREFIX}-Bold.ttf",
        "vf": source,
    }
    if any(not path.is_file() for path in sources.values()):
        raise RuntimeError("Static 400/700 and variable desktop sources are required")

    tasks: list[tuple[str, int, object, Path, Path]] = []
    for index, item in enumerate(plan):
        upstream.write_nam(WEB_DIR / "nam" / f"{index:03d}.nam", item.codepoints, item.note)
        for variant, variant_source in sources.items():
            output = WEB_DIR / "w" / variant / f"{index:03d}.woff2"
            tasks.append((variant, index, item, output, variant_source))

    def worker(task: tuple[str, int, object, Path, Path]) -> tuple[str, int, object, Path]:
        variant, index, item, output, variant_source = task
        upstream.build_woff2_subset(variant_source, output, item.codepoints)
        return variant, index, item, output

    print(f"Building {len(tasks)} Unicode-range WOFF2 chunks (static 400/700 + variable)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as executor:
        built = list(executor.map(worker, tasks))

    entries: dict[str, list[dict]] = {variant: [] for variant in sources}
    for variant, index, item, output in sorted(built, key=lambda result: (result[0], result[1])):
        entries[variant].append(_entry(index, output, item, upstream, f"w/{variant}/{output.name}"))

    css = ["/* Default production delivery: static 400/700 (transfer-budget fallback). */", ""]
    for variant in ("400", "700"):
        for entry in entries[variant]:
            css.extend((_font_face(f"./{entry['path']}", int(variant), entry["unicodeRange"]), ""))
    (WEB_DIR / "jinjer-sans.css").write_text("\n".join(css), encoding="utf-8")

    variable_css = ["/* Variable 100-900: Figma, specimen, and controlled trials. */", ""]
    for entry in entries["vf"]:
        variable_css.extend(
            (_font_face(f"./{entry['path']}", "100 900", entry["unicodeRange"], variable=True), "")
        )
    (WEB_DIR / "jinjer-sans-variable.css").write_text("\n".join(variable_css), encoding="utf-8")

    full_source = DESKTOP_DIR / f"{POSTSCRIPT_PREFIX}-VF.woff2"
    full_target = WEB_DIR / full_source.name
    shutil.copy2(full_source, full_target)
    (WEB_DIR / "jinjer-sans-full.css").write_text(
        "/* Full-font fallback for diagnostics only. */\n"
        + _font_face(f"./{full_target.name}", "100 900", variable=True)
        + "\n",
        encoding="utf-8",
    )
    (WEB_DIR / "tokens.css").write_text(
        ':root {\n  --font-family-sans: "jinjer sans", Inter, "Noto Sans JP", sans-serif;\n}\n',
        encoding="utf-8",
    )
    baseline = json.loads((Path(__file__).resolve().parents[2] / "performance-baseline.json").read_text())
    default_transfer = sum(_corpus_transfer(entries[weight], plan) for weight in ("400", "700"))
    variable_transfer = _corpus_transfer(entries["vf"], plan)
    if default_transfer > baseline["bytes"]:
        raise RuntimeError(
            f"Webfont transfer budget exceeded: {default_transfer} > {baseline['bytes']} bytes"
        )
    manifest = {
        "family": FAMILY_NAME,
        "strategy": "google-japanese",
        "subsetCount": len(plan),
        "defaultDelivery": {
            "mode": "static-400-700",
            "weights": [400, 700],
            "corpusTransferBytes": default_transfer,
            "baselineBytes": baseline["bytes"],
            "passesTransferBudget": True,
            "fonts": {
                weight: {
                    "subsetBytes": sum(entry["bytes"] for entry in entries[weight]),
                    "subsets": entries[weight],
                }
                for weight in ("400", "700")
            },
        },
        "variableDelivery": {
            "weightRange": [100, 900],
            "corpusTransferBytes": variable_transfer,
            "subsets": entries["vf"],
        },
        "full": {"path": full_target.name, "bytes": full_target.stat().st_size, "sha256": _digest(full_target)},
    }
    (WEB_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest

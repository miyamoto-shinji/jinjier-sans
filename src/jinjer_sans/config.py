from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / ".cache"
UPSTREAM_DIR = CACHE_DIR / "gen-interface-jp"
DIST_DIR = PROJECT_ROOT / "dist"
MASTER_DIR = DIST_DIR / "masters"
DESKTOP_DIR = DIST_DIR / "desktop"
WEB_DIR = DIST_DIR / "web"
RELEASE_DIR = DIST_DIR / "release"
SPECIMEN_DIR = DIST_DIR / "specimen"

FAMILY_NAME = "jinjer sans"
POSTSCRIPT_PREFIX = "jinjerSans"
VERSION = "1.0.0"
VENDOR_ID = "JNJR"


@dataclass(frozen=True)
class Master:
    public_weight: int
    style_name: str
    upstream_style: str
    inter_weight: int
    noto_weight: int


MASTERS = (
    Master(100, "Thin", "Thin", 125, 100),
    Master(400, "Regular", "Regular", 400, 465),
    Master(700, "Bold", "Bold", 700, 800),
    Master(900, "Black", "ExtraBold", 775, 900),
)
DEFAULT_WEIGHT = 400
VARIABLE_FILENAME = f"{POSTSCRIPT_PREFIX}-VF.ttf"
VARIABLE_WOFF2_FILENAME = f"{POSTSCRIPT_PREFIX}-VF.woff2"

BRAND_PRIMARY_CHARS = tuple("aegijnr0123456789@&%+-/:.,")
assert len(BRAND_PRIMARY_CHARS) == 26

CORPUS = (
    "jinjer sans ジンジャー 人事労務 給与計算 勤怠管理",
    "社員番号 JNJR-2026-0001 user@example.com",
    "2026/08/23 09:00–18:00 残業 1:30",
    "基本給 ¥350,000 支給額 ¥412,345 控除率 12.5%",
    "abcdefghijklnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "0123456789 @ & % + - / : . ,",
)

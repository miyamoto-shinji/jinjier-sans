from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from .config import CACHE_DIR, PROJECT_ROOT, UPSTREAM_DIR


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_lock() -> dict:
    return json.loads((PROJECT_ROOT / "sources.lock.json").read_text(encoding="utf-8"))


def verify_upstream(root: Path = UPSTREAM_DIR) -> None:
    lock = load_lock()
    marker = root / ".jinjer-upstream-commit"
    expected_commit = lock["genInterfaceJP"]["commit"]
    if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != expected_commit:
        raise RuntimeError(f"Upstream marker is missing or stale: {marker}")
    for relative, expected in lock["files"].items():
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"Locked upstream file is missing: {path}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"Checksum mismatch for {relative}: {actual} != {expected}")


def _safe_extract(archive: Path, destination: Path) -> Path:
    destination_resolved = destination.resolve()
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        for member in members:
            target = (destination / member.name).resolve()
            if destination_resolved not in target.parents and target != destination_resolved:
                raise RuntimeError(f"Unsafe archive member: {member.name}")
        source.extractall(destination)
    roots = [path for path in destination.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise RuntimeError("Expected exactly one root directory in the upstream archive")
    return roots[0]


def fetch_upstream() -> Path:
    if UPSTREAM_DIR.exists():
        verify_upstream()
        print(f"Upstream already verified: {UPSTREAM_DIR}")
        return UPSTREAM_DIR

    lock = load_lock()
    source = lock["genInterfaceJP"]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="jinjer-sans-fetch-") as temp_name:
        temp = Path(temp_name)
        archive = temp / "upstream.tar.gz"
        print(f"Downloading Gen Interface JP {source['version']}...")
        urllib.request.urlretrieve(source["archiveUrl"], archive)
        actual = sha256(archive)
        if actual != source["archiveSha256"]:
            raise RuntimeError(f"Archive checksum mismatch: {actual} != {source['archiveSha256']}")
        extracted = _safe_extract(archive, temp / "extract")
        shutil.move(str(extracted), str(UPSTREAM_DIR))

    (UPSTREAM_DIR / ".jinjer-upstream-commit").write_text(
        source["commit"] + "\n", encoding="utf-8"
    )
    verify_upstream()
    print(f"Fetched and verified: {UPSTREAM_DIR}")
    return UPSTREAM_DIR

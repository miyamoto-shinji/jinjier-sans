from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from .config import CACHE_DIR, PROJECT_ROOT, UPSTREAM_DIR

MAX_ARCHIVE_MEMBERS = 20_000
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_NAME_LENGTH = 512


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_lock() -> dict:
    return json.loads((PROJECT_ROOT / "sources.lock.json").read_text(encoding="utf-8"))


def source_tree_sha256(root: Path) -> str:
    """Hash every executable Python source path and its contents."""
    source_root = root / "src"
    if not source_root.is_dir():
        raise RuntimeError(f"Upstream source directory is missing: {source_root}")
    digest = hashlib.sha256()
    paths = sorted(source_root.rglob("*.py"), key=lambda path: path.relative_to(source_root).as_posix())
    if not paths:
        raise RuntimeError(f"Upstream source tree contains no Python files: {source_root}")
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"Unsafe upstream source file: {path}")
        relative = path.relative_to(source_root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256(path)))
    return digest.hexdigest()


def verify_upstream(root: Path = UPSTREAM_DIR) -> None:
    lock = load_lock()
    marker = root / ".jinjer-upstream-commit"
    expected_commit = lock["genInterfaceJP"]["commit"]
    if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != expected_commit:
        raise RuntimeError(f"Upstream marker is missing or stale: {marker}")
    expected_source_tree = lock["genInterfaceJP"]["sourceTreeSha256"]
    actual_source_tree = source_tree_sha256(root)
    if actual_source_tree != expected_source_tree:
        raise RuntimeError(
            f"Upstream executable source checksum mismatch: "
            f"{actual_source_tree} != {expected_source_tree}"
        )
    for relative, expected in lock["files"].items():
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"Locked upstream file is missing: {path}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"Checksum mismatch for {relative}: {actual} != {expected}")


def _safe_extract(archive: Path, destination: Path) -> Path:
    if not hasattr(tarfile, "data_filter"):
        raise RuntimeError("This Python runtime lacks the secure tarfile data filter")
    destination.mkdir(parents=True, exist_ok=False)
    destination_resolved = destination.resolve()
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise RuntimeError(f"Upstream archive contains too many members: {len(members)}")
        extracted_bytes = 0
        seen_targets: set[Path] = set()
        for member in members:
            if len(member.name) > MAX_ARCHIVE_NAME_LENGTH:
                raise RuntimeError(f"Archive member name is too long: {member.name[:80]}")
            if member.issym() or member.islnk():
                raise RuntimeError(f"Archive links are not allowed: {member.name}")
            if not (member.isfile() or member.isdir()):
                raise RuntimeError(f"Unsupported archive member type: {member.name}")
            if member.size > MAX_ARCHIVE_MEMBER_BYTES:
                raise RuntimeError(f"Archive member is too large: {member.name}")
            extracted_bytes += member.size
            if extracted_bytes > MAX_ARCHIVE_BYTES:
                raise RuntimeError("Upstream archive exceeds the extraction size limit")
            target = (destination / member.name).resolve()
            if destination_resolved not in target.parents and target != destination_resolved:
                raise RuntimeError(f"Unsafe archive member: {member.name}")
            if target in seen_targets:
                raise RuntimeError(f"Duplicate archive member target: {member.name}")
            seen_targets.add(target)
        source.extractall(destination, members=members, filter="data")
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

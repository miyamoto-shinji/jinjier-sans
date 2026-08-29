from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from jinjer_sans import upstream
from jinjer_sans.upstream import _safe_extract, source_tree_sha256


def _write_member(archive: tarfile.TarFile, name: str, content: bytes) -> None:
    member = tarfile.TarInfo(name)
    member.size = len(content)
    archive.addfile(member, io.BytesIO(content))


def test_source_tree_hash_detects_tampering(tmp_path: Path) -> None:
    source = tmp_path / "upstream" / "src"
    source.mkdir(parents=True)
    module = source / "builder.py"
    module.write_text("SAFE = True\n", encoding="utf-8")
    before = source_tree_sha256(tmp_path / "upstream")
    module.write_text("SAFE = False\n", encoding="utf-8")
    assert source_tree_sha256(tmp_path / "upstream") != before


def test_safe_extract_accepts_regular_files(tmp_path: Path) -> None:
    archive_path = tmp_path / "regular.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        _write_member(archive, "project/src/build.py", b"SAFE = True\n")
    root = _safe_extract(archive_path, tmp_path / "extract-regular")
    assert (root / "src" / "build.py").read_text(encoding="utf-8") == "SAFE = True\n"


def test_safe_extract_rejects_parent_traversal(tmp_path: Path) -> None:
    archive_path = tmp_path / "traversal.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        _write_member(archive, "../outside.txt", b"unsafe")
    with pytest.raises(RuntimeError, match="Unsafe archive member"):
        _safe_extract(archive_path, tmp_path / "extract-traversal")


def test_safe_extract_rejects_links(tmp_path: Path) -> None:
    archive_path = tmp_path / "link.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        link = tarfile.TarInfo("project/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "../../outside"
        archive.addfile(link)
    with pytest.raises(RuntimeError, match="Archive links are not allowed"):
        _safe_extract(archive_path, tmp_path / "extract-link")


def test_safe_extract_rejects_oversized_members(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive_path = tmp_path / "oversized.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        _write_member(archive, "project/large.bin", b"12345")
    monkeypatch.setattr(upstream, "MAX_ARCHIVE_MEMBER_BYTES", 4)
    with pytest.raises(RuntimeError, match="Archive member is too large"):
        _safe_extract(archive_path, tmp_path / "extract-oversized")

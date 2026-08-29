from __future__ import annotations

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_github_actions_are_commit_pinned_and_read_only() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    action_refs = re.findall(r"^\s*- uses:\s*[^@\s]+@([^\s#]+)", workflow, flags=re.MULTILINE)
    assert action_refs
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in action_refs)
    assert re.search(r"^permissions:\n\s+contents: read$", workflow, flags=re.MULTILINE)
    assert "persist-credentials: false" in workflow


def test_dependency_locks_require_hashes() -> None:
    for name in ("requirements-dev.lock", "requirements-fontbakery.lock"):
        lock = (PROJECT_ROOT / name).read_text(encoding="utf-8")
        assert "--hash=sha256:" in lock
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "pip install --require-hashes -r requirements-dev.lock" in makefile


def test_upstream_executable_source_is_locked() -> None:
    lock = json.loads((PROJECT_ROOT / "sources.lock.json").read_text(encoding="utf-8"))
    digest = lock["genInterfaceJP"]["sourceTreeSha256"]
    assert re.fullmatch(r"[0-9a-f]{64}", digest)


def test_specimen_security_headers_are_present() -> None:
    headers = (PROJECT_ROOT / "specimen" / "_headers").read_text(encoding="utf-8")
    assert "Content-Security-Policy:" in headers
    assert "frame-ancestors 'none'" in headers
    assert "X-Content-Type-Options: nosniff" in headers
    assert "Permissions-Policy:" in headers

"""Pin archive restoration, overwrite refusal, traversal refusal and resume.

Inputs: synthetic archive and local edits. Outputs: exact-content assertions.
Identity: verified bytes restored once; differing local bytes never replaced.
Tier: 1. Run: project Python -m pytest tests/test_workspace_transfer.py.
"""

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "transfer", Path(__file__).parents[1] / "scripts/workspace_transfer.py"
)
transfer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transfer)


def bundle(tmp_path, name="data/raw/sample.txt", claimed_hash=None):
    shared = tmp_path / "shared"
    shared.mkdir()
    payload = b"preserved source bytes\n"
    archive = shared / "part-000.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(name, payload)
    part = {"name": archive.name, "sha256": transfer.digest(archive), "files": 1}
    record = {
        "name": name,
        "bytes": len(payload),
        "sha256": claimed_hash or hashlib.sha256(payload).hexdigest(),
    }
    (shared / (archive.name + ".json")).write_text(json.dumps({**part, "files": [record]}))
    root = tmp_path / "local"
    root.mkdir()
    return shared, root, part


def test_restore_resume_and_preserve_edits(tmp_path):
    shared, root, part = bundle(tmp_path)
    assert transfer.install_part(shared, root, part) == 1
    assert (root / "data/raw/sample.txt").read_bytes() == b"preserved source bytes\n"
    assert transfer.install_part(shared, root, part) == 1
    (root / "data/raw/sample.txt").write_bytes(b"local work")
    with pytest.raises(ValueError, match="preserved"):
        transfer.install_part(shared, root, part)
    assert (root / "data/raw/sample.txt").read_bytes() == b"local work"


def test_bad_content_hash_is_not_installed(tmp_path):
    shared, root, part = bundle(tmp_path, claimed_hash="0" * 64)
    with pytest.raises(ValueError, match="hash mismatch"):
        transfer.install_part(shared, root, part)
    assert not (root / "data/raw/sample.txt").exists()


def test_legacy_output_is_restored_to_research_runs(tmp_path):
    shared, root, part = bundle(tmp_path, name="output/pilot/example.txt")
    assert transfer.install_part(shared, root, part) == 1
    assert (root / "research/runs/pilot/example.txt").read_bytes() == b"preserved source bytes\n"
    assert not (root / "output").exists()


@pytest.mark.parametrize(
    "name", ["../escape", "data/../../escape", "C:/escape", "data/raw/../escape"]
)
def test_path_traversal_refused(tmp_path, name):
    shared, root, part = bundle(tmp_path, name=name)
    with pytest.raises(ValueError, match="Unsafe"):
        transfer.install_part(shared, root, part)

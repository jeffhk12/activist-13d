"""Restore verified 13D transfer shards without overwriting different local work.

Inputs: Transfer/manifest.json, ZIP parts and file-hash receipts from the Mac.
Outputs: local data/output files and a completed-install receipt.
Identity: SHA256(each installed file) equals its verified archive receipt.
Tier: 1. Run: project Python scripts/workspace_transfer.py --shared TRANSFER_DIR.
No collection, research computations, credential access, or model calls occur.
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_destination(root, name):
    relative = PurePosixPath(name)
    if (
        not relative.parts
        or not (relative.parts[0] in ("data", "output")
                or relative.parts[:2] == ("research", "runs"))
        or relative.is_absolute()
        or ".." in relative.parts
        or PureWindowsPath(name).drive
        or "\\" in name
        or ":" in name
    ):
        raise ValueError("Unsafe transfer path: " + name)
    # Historical transfer archives keep their original member names and hashes.
    if relative.parts[0] == "output":
        relative = PurePosixPath("research/runs", *relative.parts[1:])
    target = root.joinpath(*relative.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Destination symlink escapes the working tree: " + name)
    return target


def install_part(transfer, root, part):
    name = part["name"]
    if Path(name).name != name or "\\" in name or ":" in name:
        raise ValueError("Invalid archive name")
    archive = transfer / name
    if digest(archive) != part["sha256"]:
        raise ValueError("Archive not fully synced or changed: " + name)
    receipt = json.loads((transfer / (name + ".json")).read_text(encoding="utf-8"))
    records = receipt["files"]
    if receipt["sha256"] != part["sha256"] or len(records) != part["files"]:
        raise ValueError("Archive receipt mismatch")
    names = [record["name"] for record in records]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate archive destination")
    with zipfile.ZipFile(archive) as z:
        if sorted(z.namelist()) != sorted(names):
            raise ValueError("Archive members differ from receipt")
        # Preflight the whole part before installing any of its files.
        for record in records:
            target = safe_destination(root, record["name"])
            if target.exists() and (not target.is_file() or digest(target) != record["sha256"]):
                raise ValueError("Existing local file differs; preserved: " + str(target))
            if z.getinfo(record["name"]).file_size != record["bytes"]:
                raise ValueError("Archive member size mismatch")
        for record in records:
            target = safe_destination(root, record["name"])
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".13d-transfer-", dir=target.parent)
            try:
                h = hashlib.sha256()
                with os.fdopen(fd, "wb") as dst, z.open(record["name"]) as src:
                    for block in iter(lambda: src.read(1024 * 1024), b""):
                        dst.write(block)
                        h.update(block)
                if h.hexdigest() != record["sha256"]:
                    raise ValueError("Extracted file hash mismatch: " + record["name"])
                # Hard linking installs only if the destination is still absent;
                # unlike replace(), it cannot overwrite an intervening local edit.
                os.link(temporary, target)
            finally:
                Path(temporary).unlink(missing_ok=True)
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared", type=Path, required=True)
    args = parser.parse_args()
    transfer = args.shared.resolve()
    marker = transfer / "manifest.json"
    if not marker.is_file():
        raise RuntimeError("The full transfer is not ready. Wait for the Mac completion manifest.")
    manifest = json.loads(marker.read_text(encoding="utf-8"))
    if manifest["schema"] != 1:
        raise ValueError("Unknown transfer schema")
    count = 0
    for part in manifest["parts"]:
        if shutil.disk_usage(ROOT).free < 20 * 1024**3:
            raise RuntimeError(
                "Keep at least 20 GiB free; completed files are preserved for resume."
            )
        count += install_part(transfer, ROOT, part)
        print("Verified and installed:", part["name"], flush=True)
    if count != manifest["files"]:
        raise ValueError("Total file count differs from manifest")
    receipt = {
        "computer": platform.node(),
        "files": count,
        "manifest_sha256": digest(marker),
        "parts": manifest["parts"],
    }
    (ROOT / ".workspace-transfer.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print("13D LOCAL DATA INSTALL VERIFIED:", count, "files")


if __name__ == "__main__":
    main()

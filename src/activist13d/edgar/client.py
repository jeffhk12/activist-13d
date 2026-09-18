"""Download SEC evidence with a declared contact and immutable disk cache.

Inputs: SEC URL, cache path, EDGAR_USER_AGENT. Outputs: exact response bytes
and a provenance sidecar. Identity: sha256(cache bytes) = recorded digest.
Tier: 1
Run: imported by scripts/collect_pilot.py; no paid endpoints.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests


class SecClient:
    """Single-process client, at most two requests/second; no automatic retries.

    ``budget_path`` makes a live run restart-safe: only successful, newly
    cached responses count, and the counter is atomically persisted before the
    next request.  Callers may set conservative limits for a bounded run.
    """

    def __init__(
        self,
        offline: bool = False,
        budget_path: Path | None = None,
        max_successes: int = 200,
        max_new_bytes: int = 3 * 1024 * 1024 * 1024,
        max_response_bytes: int = 100 * 1024 * 1024,
    ):
        self.offline = offline
        self.last_call = 0.0
        self.budget_path = budget_path
        self.max_successes = max_successes
        self.max_new_bytes = max_new_bytes
        self.max_response_bytes = max_response_bytes

    def _budget(self) -> dict:
        if self.budget_path is None or not self.budget_path.exists():
            return {"successful_requests": 0, "new_raw_bytes": 0}
        data = json.loads(self.budget_path.read_text(encoding="utf-8"))
        return {
            "successful_requests": int(data.get("successful_requests", 0)),
            "new_raw_bytes": int(data.get("new_raw_bytes", 0)),
        }

    def _write_budget(self, budget: dict) -> None:
        if self.budget_path is None:
            return
        self.budget_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.budget_path.with_suffix(self.budget_path.suffix + ".tmp")
        temporary.write_text(json.dumps(budget, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.budget_path)

    def fetch(self, url: str, destination: Path) -> bytes:
        if urlparse(url).hostname not in {"www.sec.gov", "data.sec.gov"}:
            raise ValueError("Only official SEC hosts are allowed")
        if destination.exists():
            payload = destination.read_bytes()
            meta = json.loads(destination.with_suffix(destination.suffix + ".meta.json").read_text())
            if meta["url"] != url or meta["sha256"] != hashlib.sha256(payload).hexdigest():
                raise ValueError(f"Cache provenance mismatch: {destination}")
            return payload
        if self.offline:
            raise FileNotFoundError(f"Offline cache missing: {destination}")
        user_agent = os.environ.get("EDGAR_USER_AGENT", "").strip()
        if not re.search(r"\S+@\S+\.\S+", user_agent) or "example." in user_agent:
            raise ValueError("Set EDGAR_USER_AGENT to a real name and contact email")
        budget = self._budget()
        if budget["successful_requests"] >= self.max_successes:
            raise RuntimeError("SEC successful-request budget exhausted")
        time.sleep(max(0, 0.5 - (time.monotonic() - self.last_call)))
        self.last_call = time.monotonic()
        response = requests.get(
            url, headers={"User-Agent": user_agent}, timeout=(15, 90), stream=True
        )
        response.raise_for_status()
        chunks = []
        size = 0
        if hasattr(response, "iter_content"):
            iterator = response.iter_content(chunk_size=64 * 1024)
        else:  # small test doubles retain the original response contract
            iterator = [response.content]
        for chunk in iterator:
            if not chunk:
                continue
            size += len(chunk)
            if size > self.max_response_bytes:
                raise ValueError("SEC response exceeds per-response size limit")
            if budget["new_raw_bytes"] + size > self.max_new_bytes:
                raise RuntimeError("SEC new-raw-data budget exhausted")
            chunks.append(chunk)
        payload = b"".join(chunks)
        if not payload or b"Your Request Originates from an Undeclared Automated Tool" in payload:
            raise ValueError("SEC returned an empty response or access-denial page")
        meta = {
            "url": url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "content_type": response.headers.get("Content-Type"),
        }
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        if temporary.exists():
            raise FileExistsError(f"Unfinished cache write present: {temporary}")
        with temporary.open("xb") as handle:
            handle.write(payload)
        temporary.replace(destination)
        metadata_path = destination.with_suffix(destination.suffix + ".meta.json")
        metadata_temporary = metadata_path.with_suffix(metadata_path.suffix + ".tmp")
        metadata_temporary.write_text(
            json.dumps(meta, indent=2) + "\n", encoding="utf-8"
        )
        metadata_temporary.replace(metadata_path)
        budget["successful_requests"] += 1
        budget["new_raw_bytes"] += len(payload)
        self._write_budget(budget)
        return payload

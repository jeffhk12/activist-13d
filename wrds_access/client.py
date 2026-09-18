"""Bounded, read-only WRDS Data API access with frozen offline replay.

Inputs: allowlisted table, exact filters, row limit, explicit online opt-in.
Outputs: original JSON and a request/timestamp/hash provenance envelope.
Identity: n = len(results); SHA-256(raw response) verifies frozen evidence.
No estimators, joins, research-universe selection, or pagination are performed.
Tier: 1
Run: .venv/bin/python wrds_access/run.py --help
"""

import hashlib
import json
import os
import platform
import re
from datetime import date, datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://wrds-api.wharton.upenn.edu/data/"
SCOPES = {
    "crsp.dsf": ("permno", "date"),
    "comp.funda": ("gvkey", "fyear"),
    "audit.feed31_shareholder_activism": ("iss_file_date",),
}
MAX_ROWS = 5
MAX_BYTES = 1_000_000


class AccessError(RuntimeError):
    """A safe-to-display refusal, without transport or credential details."""


def load_token(env_file=ROOT / ".env"):
    """Load only WRDS_API_KEY; an explicitly empty environment disables access."""
    token = os.environ.get("WRDS_API_KEY")
    if token is None:
        try:
            lines = Path(env_file).read_text().splitlines()
        except OSError:
            raise AccessError("Cannot read WRDS credential file") from None
        for line in lines:
            match = re.fullmatch(r"\s*(?:export\s+)?WRDS_API_KEY\s*=\s*(.*?)\s*", line)
            if match:
                token = match[1].strip("\"'")
                break
    if not token or not re.fullmatch(r"[A-Za-z0-9._~-]+", token):
        raise AccessError("A valid WRDS_API_KEY is required")
    return token


class Client:
    def __init__(self, cache=ROOT / "data/raw/wrds/v1", *, online=False):
        self.cache = Path(cache)
        self.online = online

    def _request(self, table, method, params):
        if table not in SCOPES or method not in {"GET", "OPTIONS"}:
            raise AccessError("Only approved read-only table requests are allowed")
        request = {"url": BASE + table + "/", "method": method, "params": params}
        key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        path = self.cache / (key + ".json")
        if path.exists():
            envelope = json.loads(path.read_text())
            raw = envelope["raw_response"].encode()
            if (
                envelope["request"] != request
                or hashlib.sha256(raw).hexdigest() != envelope["sha256"]
            ):
                raise AccessError("Cached response failed integrity verification")
            return json.loads(raw), envelope
        if not self.online:
            raise AccessError("Cache miss; use --online explicitly to fetch this bounded request")
        token = load_token()
        try:
            with requests.Session() as session:
                # Avoid implicit .netrc authentication replacing the Token header.
                session.trust_env = False
                with session.request(
                    method,
                    request["url"],
                    params=params,
                    headers={"Authorization": "Token " + token, "Accept": "application/json"},
                    timeout=(10, 45),
                    allow_redirects=False,
                    stream=True,
                ) as response:
                    if response.status_code != 200:
                        raise AccessError(
                            f"WRDS returned HTTP {response.status_code}; response details suppressed"
                        )
                    chunks = []
                    size = 0
                    for chunk in response.iter_content(8192):
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise AccessError("WRDS response exceeded the byte cap")
                        chunks.append(chunk)
                    raw = b"".join(chunks)
        except requests.RequestException:
            raise AccessError("WRDS connection failed; transport details suppressed") from None
        if token.encode() in raw:
            raise AccessError("Credential appeared in response; refusing to cache")
        try:
            payload = json.loads(raw)
        except ValueError:
            raise AccessError("WRDS returned non-JSON content") from None
        envelope = {
            "version": 1,
            "request": request,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "raw_response": raw.decode("utf-8"),
            "python": platform.python_version(),
            "requests": requests.__version__,
        }
        self.cache.mkdir(parents=True, exist_ok=True)
        # Never overwrite frozen raw evidence. Concurrent writers fail explicitly.
        with path.open("x") as handle:
            json.dump(envelope, handle, indent=2)
        return payload, envelope

    def schema(self, table):
        payload, provenance = self._request(table, "OPTIONS", {})
        if not isinstance(payload, dict) or not isinstance(payload.get("fields"), dict):
            raise AccessError("Unexpected WRDS schema response")
        return payload["fields"], provenance

    def sample(self, table, filters, *, limit=1):
        if table not in SCOPES:
            raise AccessError("Table is outside the approved scope")
        if type(limit) is not int or not 1 <= limit <= MAX_ROWS:
            raise AccessError("Sample limit must be an integer from 1 through 5")
        if not isinstance(filters, dict) or not all(key in filters for key in SCOPES[table]):
            raise AccessError("Required exact identifier/date scope is missing")
        fields, _ = self.schema(table)
        normalized = {}
        for key, value in filters.items():
            meta = fields.get(key, {})
            if not meta.get("filter_field"):
                raise AccessError("Unsupported filter; WRDS may silently ignore it")
            value = str(value)
            if not re.fullmatch(r"[A-Za-z0-9.-]{1,32}", value):
                raise AccessError("Only single, exact filter values are supported")
            if meta["type"] == "date":
                try:
                    if date.fromisoformat(value).isoformat() != value:
                        raise ValueError
                except ValueError:
                    raise AccessError("Date filters must be YYYY-MM-DD") from None
            elif meta["type"] == "integer" and not re.fullmatch(r"[0-9]+", value):
                raise AccessError("Integer filter requires digits")
            normalized[key] = value
        payload, provenance = self._request(table, "GET", {**normalized, "limit": limit})
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise AccessError("Unexpected WRDS sample response")
        rows = payload["results"]
        if len(rows) > limit:
            raise AccessError("WRDS ignored the row limit")
        for row in rows:
            if not isinstance(row, dict) or any(
                str(row.get(k)) != v for k, v in normalized.items()
            ):
                raise AccessError("WRDS returned a row outside the requested scope")
        # next may use HTTP; it is never followed. count is not a downloaded row count.
        return rows, provenance

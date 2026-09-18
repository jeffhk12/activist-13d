"""Shared fixtures and suite-wide safety pins.

Only genuinely duplicated setup belongs here. The bar is "this exact definition
already appeared in more than one module".

The credential blanking below is not a fixture and not optional — see the note.

Tier: 0
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Pin every provider credential OFF for the whole suite, before anything
# imports a module that might read one.
#
# Assignment, NOT setdefault. This repo sits next to a pipeline that calls paid
# extraction endpoints across several vendors. No test in this suite should
# ever reach one, including for someone who exports a key in their shell — a
# stray live key turns `pytest` into a billable batch job against a third party,
# and makes any test that compares extraction output non-deterministic.
#
# Tests that exercise the adapter set these themselves via monkeypatch and stub
# the transport.
# ---------------------------------------------------------------------------
for _cred in (
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
    "TOGETHER_API_KEY",
    "WRDS_PASSWORD",
):
    os.environ[_cred] = ""

# Route any cache the code builds at a throwaway location rather than the real
# data tree, so a test can never poison or evict the expensive response cache.
os.environ["ACTIVIST13D_CACHE_DIR"] = ""


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = REPO_ROOT / "data" / "raw"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def data_raw() -> Path:
    """The archived-filings tree. Absent in CI; tests needing it should skip."""
    return DATA_RAW


@pytest.fixture()
def cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A per-test fetch cache, isolated from data/raw."""
    d = tmp_path / "cache"
    d.mkdir()
    monkeypatch.setenv("ACTIVIST13D_CACHE_DIR", str(d))
    return d


def pytest_collection_modifyitems(config, items):
    """Skip filing-dependent tests when the archive is not present."""
    if DATA_RAW.exists() and any(DATA_RAW.iterdir()):
        return
    skip = pytest.mark.skip(reason="data/raw is empty — archived filings not present")
    for item in items:
        if "data_raw" in getattr(item, "fixturenames", ()):
            item.add_marker(skip)

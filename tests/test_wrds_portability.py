"""Tier: 1. Import offline tools without POSIX locks; retain collector exclusion.

Uses temporary files and an empty task plan. No provider access or raw collection.
Run: project Python -m pytest tests/test_wrds_portability.py.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


def load():
    path = Path(__file__).parents[1] / 'scripts/data_collection/wrds_collect.py'
    spec = importlib.util.spec_from_file_location('portable_wrds_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_offline_wrds_import_without_fcntl(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, 'fcntl', None)
    module = load()
    assert module.FrozenClient(online=False).online is False


def test_collector_excludes_second_owner_and_releases(tmp_path, monkeypatch):
    from activist13d.file_lock import acquire_exclusive, release
    module = load()
    monkeypatch.setattr(module, 'OUT', tmp_path)
    monkeypatch.setattr(module, 'tasks', lambda: [])
    client = SimpleNamespace(network_calls=0)
    with (tmp_path / 'worker.lock').open('a+') as held:
        acquire_exclusive(held)
        try:
            with pytest.raises(module.Refusal, match='already running'):
                module.collect(client)
        finally:
            release(held)
    module.collect(client)
    # A second successful run proves the first released its lock.
    module.collect(client)
    assert client.network_calls == 0

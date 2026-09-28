"""Pins for relocating historical evidence without opening the legacy copy."""
from pathlib import Path

import pytest

from activist13d.local_paths import LEGACY_ROOT, resolve_project_path


def test_relative_and_historical_paths_agree(tmp_path):
    expected = tmp_path / 'data/raw/example.txt'
    assert resolve_project_path('data/raw/example.txt', tmp_path) == expected
    assert resolve_project_path(LEGACY_ROOT / 'data/raw/example.txt', tmp_path) == expected
    assert resolve_project_path(expected, tmp_path) == expected


@pytest.mark.parametrize('path', ['../escape', '/tmp/outside-project', str(LEGACY_ROOT / '../other')])
def test_refuses_escape(tmp_path, path):
    with pytest.raises(ValueError):
        resolve_project_path(path, tmp_path)


def test_refuses_symlink_to_legacy(tmp_path):
    try:
        (tmp_path / 'raw').symlink_to(LEGACY_ROOT / 'data/raw', target_is_directory=True)
    except OSError as exc:
        if getattr(exc, 'winerror', None) == 1314:
            pytest.skip('Windows account lacks symbolic-link creation privilege')
        raise
    with pytest.raises(ValueError):
        resolve_project_path('raw/file.txt', tmp_path)


def test_does_not_fall_back_to_existing_legacy_path(tmp_path):
    result = resolve_project_path(LEGACY_ROOT / 'README.md', tmp_path)
    assert result == tmp_path / 'README.md'
    assert not result.exists()


@pytest.mark.parametrize('old,new', [
    ('output/pilot-filings/example.md', 'research/runs/pilot-filings/example.md'),
    ('outputs/13d-group-review-20260922/index.html', 'review/current/index.html'),
    ('outputs/13d-human-review-52-20260923/index.html', 'review/drafts/human-first-52/index.html'),
    ('outputs/other/index.html', 'review/archive/other/index.html'),
    ('protocol/categories-v1.yaml', 'research/protocol/categories-v1.yaml'),
])
def test_old_layout_maps_without_changing_manifests(tmp_path, old, new):
    assert resolve_project_path(old, tmp_path) == tmp_path / new
    assert resolve_project_path(LEGACY_ROOT / old, tmp_path) == tmp_path / new
    assert resolve_project_path(tmp_path / old, tmp_path) == tmp_path / new
    assert resolve_project_path(tmp_path / new, tmp_path) == tmp_path / new

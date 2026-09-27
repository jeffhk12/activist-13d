"""Resolve historical project paths against the active local checkout.

Inputs: a source path from an immutable manifest and the current project root.
Output: a path within that root; no source-manifest mutation or legacy fallback.
Identity: legacy_root / relative == current_root / relative after relocation.
Tier: 1. Tested by tests/test_local_paths.py; no network or filesystem writes.
"""
from pathlib import Path

LEGACY_ROOT = Path('/Users/jefflu/Documents/GitHub-Repos/activist-13d')
LAYOUT_MOVES = (
    ('outputs/13d-group-review-20260922', 'review/current'),
    ('outputs/13d-human-review-52-20260923', 'review/drafts/human-first-52'),
    ('outputs', 'review/archive'),
    ('output', 'research/runs'),
    ('docs', 'research/docs'),
    ('protocol', 'research/protocol'),
)


def resolve_project_path(value: str | Path, root: Path) -> Path:
    root = root.resolve()
    path = Path(value)
    if path.is_absolute():
        if path.is_relative_to(LEGACY_ROOT):
            path = root / path.relative_to(LEGACY_ROOT)
        elif not path.is_relative_to(root):
            raise ValueError(f'Path is outside the project: {path}')
    else:
        path = root / path
    relative = path.relative_to(root)
    for old, new in LAYOUT_MOVES:
        if relative.is_relative_to(Path(old)):
            path = root / new / relative.relative_to(old)
            break
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f'Path or symlink escapes the local project: {path}')
    return resolved

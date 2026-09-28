"""Preserve and verify cross-computer research handoffs without running research.

Inputs: local data/review/run files and immutable shared snapshot manifests.
Outputs: checked ZIP deltas, local recovery copies, and receiving receipts.
Identity: every received byte must match its manifest SHA256; replacing a review
file additionally requires its prior hash and a preserved local recovery copy.
Tier: 1. Run: project Python scripts/workspace_handoff.py start|finish --shared DIR.
Raw data and historical runs are append-only; deletions require separate review.
"""
from pathlib import Path, PurePosixPath, PureWindowsPath
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AREAS = ('data', 'review', 'research/runs')
SKIP_DIRS = {'__pycache__', '.pytest_cache', 'workspace-validation'}
SKIP_NAMES = {'.DS_Store', 'Thumbs.db'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def destination(root, name):
    p = PurePosixPath(name)
    if (not p.parts or p.is_absolute() or '..' in p.parts or '\\' in name
            or ':' in name or PureWindowsPath(name).drive
            or not (p.parts[0] in ('data', 'review') or p.parts[:2] == ('research', 'runs'))):
        raise ValueError('Unsafe handoff path: ' + name)
    target = root.joinpath(*p.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escapes the project: ' + name)
    if target.is_symlink() or any(x.is_symlink() for x in target.parents if x != root and root in x.parents):
        raise ValueError('Managed payload cannot traverse a symbolic link: ' + name)
    return target


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.handoff-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def records(manifest):
    rows = manifest['files']
    indexed = {r['path']: r for r in rows}
    if len(indexed) != len(rows) or len({n.casefold() for n in indexed}) != len(rows):
        raise ValueError('Duplicate or Windows-colliding manifest paths')
    return indexed


def load_snapshot(shared, snapshot):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', snapshot):
        raise ValueError('Unsafe snapshot identifier')
    folder = shared / 'snapshots' / snapshot
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['schema'] != 1 or manifest['id'] != snapshot:
        raise ValueError('Unsupported snapshot')
    records(manifest)
    return folder, manifest


def latest(shared):
    marker = json.loads((shared / 'latest.json').read_text(encoding='utf-8'))
    folder, manifest = load_snapshot(shared, marker['id'])
    if digest(folder / 'manifest.json') != marker['sha256']:
        raise ValueError('Manifest has not fully synchronized')
    return marker, manifest


def inventory(root, omitted=(), archived_databases=None):
    omitted = set(omitted)
    archived_databases = archived_databases or {}
    rows = []
    for area in AREAS:
        for current, dirs, names in os.walk(root / area, followlinks=False):
            dirs[:] = sorted(n for n in dirs if n not in SKIP_DIRS and not (Path(current) / n).is_symlink())
            for name in sorted(names):
                p = Path(current) / name
                rel = p.relative_to(root).as_posix()
                if (p.is_symlink() or rel in omitted or name in SKIP_NAMES
                        or name.startswith('~$') or name.endswith(('.partial', '.lock'))):
                    continue
                database = p.suffix.lower() in {'.db', '.sqlite', '.sqlite3'}
                if (name.lower().startswith('.env') or p.suffix.lower() in {'.pem', '.key'}
                        or (database and (rel not in archived_databases
                            or any(Path(str(p) + suffix).exists() for suffix in ('-wal', '-shm', '-journal'))))):
                    raise ValueError('Private settings or live database require separate handling: ' + rel)
                destination(root, rel)
                before = p.stat()
                sha = digest(p)
                if database and sha != archived_databases[rel]:
                    raise ValueError('Archived database changed; create a consistent snapshot separately: ' + rel)
                after = p.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ValueError('File changed while reading: ' + rel)
                rows.append({'path': rel, 'bytes': after.st_size, 'sha256': sha})
    return sorted(rows, key=lambda r: r['path'])


def verify_local(root, manifest):
    for name, row in records(manifest).items():
        p = destination(root, name)
        if not p.is_file() or digest(p) != row['sha256']:
            raise ValueError('Local file differs; preserved: ' + name)


def state_path(root):
    return root / '.workspace-local/handoff/state.json'


def initialize(root, shared):
    marker, manifest = latest(shared)
    expected = records(manifest)
    known = set(expected)
    aliases = {x['path'] for x in manifest.get('links', [])}
    current = records({'files': inventory(root, aliases, {n: r['sha256'] for n, r in expected.items()})})
    for name, row in expected.items():
        if name not in current or current[name] != row:
            raise ValueError('Local file differs; preserved: ' + name)
    extras = [name for name in current if name not in known]
    state = {'id': marker['id'], 'manifest_sha256': marker['sha256'], 'local_only': extras}
    if state_path(root).exists():
        raise ValueError('Already initialized; use start or finish')
    atomic_json(state_path(root), state)
    return state


def publish(root, shared, code):
    state = json.loads(state_path(root).read_text(encoding='utf-8'))
    marker, base = latest(shared)
    if marker['id'] != state['id'] or marker['sha256'] != state['manifest_sha256']:
        raise ValueError('A different handoff exists. Start Work before making another handoff.')
    old = records(base)
    archived_databases = {n: r['sha256'] for n, r in old.items()}
    aliases = {x['path'] for x in base.get('links', [])}
    current = inventory(root, set(state['local_only']) | aliases, archived_databases)
    new = records({'files': current})
    if set(old) - set(new):
        raise ValueError('Managed files were deleted. Restore or archive them before handoff.')
    changed = [n for n in new if n not in old or old[n]['sha256'] != new[n]['sha256']]
    if any(n in old and not n.startswith('review/') for n in changed):
        raise ValueError('Raw data or historical output changed. Preserve a new version instead.')
    snapshot = uuid.uuid4().hex
    folder = shared / 'snapshots' / snapshot
    folder.mkdir(parents=True, exist_ok=False)
    parts = []
    pending = list(changed)
    while pending:
        group, size = [], 0
        while pending and (size < 256 * 1024**2 or not group):
            name = pending.pop(0)
            group.append(name)
            size += new[name]['bytes']
        filename = f'part-{len(parts):04d}.zip'
        with zipfile.ZipFile(folder / filename, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as z:
            for name in group:
                z.write(destination(root, name), name)
        with zipfile.ZipFile(folder / filename) as z:
            for name in group:
                h = hashlib.sha256()
                with z.open(name) as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        h.update(block)
                if h.hexdigest() != new[name]['sha256']:
                    raise ValueError('Payload changed while packaging: ' + name)
        parts.append({'name': filename, 'sha256': digest(folder / filename), 'files': group})
    manifest = {'schema': 1, 'id': snapshot, 'parent': marker, 'code': code,
                'computer': platform.node(), 'files': current, 'links': base.get('links', []), 'parts': parts}
    atomic_json(folder / 'manifest.json', manifest)
    if latest(shared)[0] != marker:
        raise ValueError('Another computer published during packaging; incomplete snapshot retained.')
    # A second inventory detects intervening edits, additions and removals.
    if inventory(root, set(state['local_only']) | aliases, archived_databases) != current:
        raise ValueError('Local files changed during handoff. Close project editors and retry.')
    next_marker = {'id': snapshot, 'sha256': digest(folder / 'manifest.json')}
    atomic_json(shared / 'latest.json', next_marker)
    atomic_json(state_path(root), {**state, 'id': snapshot, 'manifest_sha256': next_marker['sha256']})
    return manifest


def receive_one(root, shared, marker, manifest):
    state = json.loads(state_path(root).read_text(encoding='utf-8'))
    parent = manifest['parent']
    if parent != {'id': state['id'], 'sha256': state['manifest_sha256']}:
        raise ValueError('Previous handoff differs; reconcile before receiving')
    old_folder, old = load_snapshot(shared, state['id'])
    if digest(old_folder / 'manifest.json') != state['manifest_sha256']:
        raise ValueError('Previous manifest changed')
    before, after = records(old), records(manifest)
    if set(before) - set(after):
        raise ValueError('Incoming handoff deletes managed evidence')
    changed = {n for n in after if n not in before or before[n]['sha256'] != after[n]['sha256']}
    if any(n in before and not n.startswith('review/') for n in changed):
        raise ValueError('Incoming handoff replaces immutable evidence')
    folder, _ = load_snapshot(shared, marker['id'])
    stage = root / '.workspace-local/handoff/staging' / marker['id']
    stage.mkdir(parents=True, exist_ok=True)
    backup = root / '.workspace-local/handoff/recovery' / marker['id']
    journal = stage / 'prepared.json'
    resuming = journal.exists()
    if resuming and json.loads(journal.read_text(encoding='utf-8')) != {'marker': marker, 'parent': parent}:
        raise ValueError('Recovery journal differs')
    applied = set()
    for name, row in before.items():
        target = destination(root, name)
        actual = digest(target) if target.is_file() else None
        if actual == row['sha256']:
            continue
        preserved = destination(backup, name)
        if (resuming and name in changed and actual == after[name]['sha256']
                and preserved.is_file() and digest(preserved) == row['sha256']):
            applied.add(name)
            continue
        raise ValueError('Local file differs; preserved: ' + name)
    seen = set()
    for part in manifest['parts']:
        if not re.fullmatch(r'part-[0-9]{4}\.zip', part['name']):
            raise ValueError('Invalid archive name')
        archive = folder / part['name']
        if digest(archive) != part['sha256']:
            raise ValueError('Archive is incomplete or changed')
        with zipfile.ZipFile(archive) as z:
            if sorted(z.namelist()) != sorted(part['files']) or len(set(z.namelist())) != len(z.namelist()):
                raise ValueError('Archive members differ')
            for name in part['files']:
                if name not in changed or name in seen:
                    raise ValueError('Unexpected or repeated payload')
                seen.add(name)
                if z.getinfo(name).file_size != after[name]['bytes']:
                    raise ValueError('Payload size differs from manifest')
                target = destination(stage, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                fd, temporary = tempfile.mkstemp(prefix='.payload-', dir=target.parent)
                try:
                    with z.open(name) as src, os.fdopen(fd, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    if digest(Path(temporary)) != after[name]['sha256']:
                        raise ValueError('Payload hash mismatch')
                    # Replace the staging directory entry rather than writing
                    # through a possible hard link from an interrupted receive.
                    os.replace(temporary, target)
                finally:
                    Path(temporary).unlink(missing_ok=True)
    if seen != changed:
        raise ValueError('Missing payloads')
    # Validate every destination before installing any data.
    for name in changed:
        p = destination(root, name)
        if name not in before and p.exists():
            if resuming and p.is_file() and digest(p) == after[name]['sha256']:
                applied.add(name)
            else:
                raise ValueError('An incoming file would replace local work: ' + name)
    atomic_json(journal, {'marker': marker, 'parent': parent})
    for name in sorted(changed):
        if name in applied:
            continue
        target = destination(root, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if name in before:
            if digest(target) != before[name]['sha256']:
                raise ValueError('Concurrent local edit detected')
            preserved = destination(backup, name)
            preserved.parent.mkdir(parents=True, exist_ok=True)
            if not preserved.exists():
                shutil.copy2(target, preserved)
            if digest(preserved) != before[name]['sha256']:
                raise ValueError('Recovery copy differs')
            if digest(target) != before[name]['sha256']:
                raise ValueError('Concurrent local edit detected after preservation')
            os.replace(destination(stage, name), target)
        else:
            os.link(destination(stage, name), target)
            destination(stage, name).unlink()
    verify_local(root, manifest)
    atomic_json(state_path(root), {**state, 'id': marker['id'], 'manifest_sha256': marker['sha256']})


def receive(root, shared):
    marker, manifest = latest(shared)
    state = json.loads(state_path(root).read_text(encoding='utf-8'))
    chain = []
    visited = set()
    while marker['id'] != state['id']:
        if marker['id'] in visited:
            raise ValueError('Cycle in snapshot history')
        visited.add(marker['id'])
        chain.append((marker, manifest))
        marker = manifest['parent']
        if not marker:
            raise ValueError('Local state is not an ancestor of the current handoff')
        folder, manifest = load_snapshot(shared, marker['id'])
        if digest(folder / 'manifest.json') != marker['sha256']:
            raise ValueError('Historical manifest differs')
    if marker['sha256'] != state['manifest_sha256']:
        raise ValueError('Local baseline hash differs')
    for next_marker, next_manifest in reversed(chain):
        receive_one(root, shared, next_marker, next_manifest)
    verify_local(root, latest(shared)[1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['initialize', 'start', 'finish', 'check'])
    parser.add_argument('--shared', type=Path, required=True)
    args = parser.parse_args()
    def git(*command):
        return subprocess.check_output(['git', '-C', str(ROOT), *command], text=True).strip()
    if git('status', '--porcelain'):
        raise ValueError('Code has uncommitted changes; preserve and commit before handoff')
    if args.action == 'finish':
        branch = git('branch', '--show-current')
        if not branch:
            raise ValueError('Use a named branch')
        git('push', 'origin', f'HEAD:refs/heads/{branch}')
        commit = git('rev-parse', 'HEAD')
        if git('ls-remote', 'origin', f'refs/heads/{branch}').split()[0] != commit:
            raise ValueError('Published source commit differs')
        publish(ROOT, args.shared, {'branch': branch, 'commit': commit})
        print('Finish verified. Wait for Drive synchronization before starting on the other computer.')
    else:
        _, manifest = latest(args.shared)
        if args.action == 'start' and git('branch', '--show-current') == manifest['code']['branch']:
            if git('rev-parse', 'HEAD') != manifest['code']['commit']:
                git('fetch', 'origin', manifest['code']['branch'])
                if git('rev-parse', 'FETCH_HEAD') != manifest['code']['commit']:
                    raise ValueError('GitHub and the received handoff differ; wait for synchronization')
                git('merge', '--ff-only', manifest['code']['commit'])
        if manifest['code'] != {'branch': git('branch', '--show-current'), 'commit': git('rev-parse', 'HEAD')}:
            raise ValueError('Source and handoff differ. Reconcile Git branch/commit before receiving data.')
        if args.action == 'initialize':
            state = initialize(ROOT, args.shared)
            print('Baseline verified. Preserved local-only files outside handoff:', len(state['local_only']))
        elif args.action == 'start':
            receive(ROOT, args.shared)
            print('Start verified. Only this computer should now edit the project.')
        else:
            verify_local(ROOT, manifest)
            print('Current managed files match the shared handoff.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        raise SystemExit('Handoff stopped: ' + str(exc))

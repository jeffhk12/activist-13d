"""Handoff integrity, evidence preservation, conflict refusal and multi-step receiving."""
import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('handoff', Path(__file__).parents[1] / 'scripts/workspace_handoff.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


@pytest.fixture
def pair(tmp_path):
    a, b, shared = [tmp_path / n for n in ['a', 'b', 'shared']]
    for root in [a, b]:
        (root / 'data/raw').mkdir(parents=True)
        (root / 'data/raw/filing.txt').write_text('Preserved filing evidence')
        (root / 'review/current').mkdir(parents=True)
        (root / 'review/current/answers.csv').write_text('filing,label\n1,\n')
    folder = shared / 'snapshots/baseline'
    folder.mkdir(parents=True)
    manifest = {'schema': 1, 'id': 'baseline', 'parent': None, 'code': {'branch': 'main', 'commit': 'abc'}, 'files': h.inventory(a), 'links': [], 'parts': []}
    h.atomic_json(folder / 'manifest.json', manifest)
    h.atomic_json(shared / 'latest.json', {'id': 'baseline', 'sha256': h.digest(folder / 'manifest.json')})
    h.initialize(a, shared)
    h.initialize(b, shared)
    return a, b, shared


def test_review_edit_preserves_receiver_preimage_and_new_evidence(pair):
    a, b, shared = pair
    name = 'review/current/answers.csv'
    old = (b / name).read_bytes()
    (a / name).write_text('filing,label\n1,human answer\n')
    (a / 'data/raw/new.txt').write_text('New filing')
    manifest = h.publish(a, shared, {'branch': 'main', 'commit': 'abc'})
    h.receive(b, shared)
    assert (b / name).read_bytes() == (a / name).read_bytes()
    assert (b / '.workspace-local/handoff/recovery' / manifest['id'] / name).read_bytes() == old
    assert (b / 'data/raw/new.txt').read_text() == 'New filing'


def test_local_human_edit_refuses_without_overwrite(pair):
    a, b, shared = pair
    name = 'review/current/answers.csv'
    (a / name).write_text('Mac answer')
    h.publish(a, shared, {})
    (b / name).write_text('Windows answer')
    with pytest.raises(ValueError, match='Local file differs'):
        h.receive(b, shared)
    assert (b / name).read_text() == 'Windows answer'


def test_tampered_archive_refuses_before_install(pair):
    a, b, shared = pair
    (a / 'data/raw/new.txt').write_text('new')
    m = h.publish(a, shared, {})
    (shared / 'snapshots' / m['id'] / 'part-0000.zip').write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='Archive is incomplete'):
        h.receive(b, shared)
    assert not (b / 'data/raw/new.txt').exists()


def test_existing_new_destination_is_preserved(pair):
    a, b, shared = pair
    (a / 'data/raw/new.txt').write_text('Mac')
    h.publish(a, shared, {})
    (b / 'data/raw/new.txt').write_text('Windows')
    with pytest.raises(ValueError, match='replace local work'):
        h.receive(b, shared)
    assert (b / 'data/raw/new.txt').read_text() == 'Windows'


@pytest.mark.parametrize('action', ['change', 'delete'])
def test_original_raw_evidence_cannot_change(pair, action):
    a, b, shared = pair
    p = a / 'data/raw/filing.txt'
    if action == 'change':
        p.write_text('Changed evidence')
    else:
        p.unlink()
    with pytest.raises(ValueError):
        h.publish(a, shared, {})
    assert h.latest(shared)[0]['id'] == 'baseline'


def test_multiple_missed_handoffs_received_in_order(pair):
    a, b, shared = pair
    for n in [1, 2]:
        (a / f'data/raw/new{n}.txt').write_text(str(n))
        h.publish(a, shared, {})
    h.receive(b, shared)
    assert (b / 'data/raw/new1.txt').read_text() == '1'
    assert (b / 'data/raw/new2.txt').read_text() == '2'
    assert json.loads(h.state_path(b).read_text())['id'] == h.latest(shared)[0]['id']


def test_stale_sender_cannot_publish(pair):
    a, b, shared = pair
    h.publish(a, shared, {})
    with pytest.raises(ValueError, match='different handoff'):
        h.publish(b, shared, {})


@pytest.mark.parametrize('name', ['../outside', '/data/file', 'data/../../file', 'C:/data/file', 'data\\file', 'scripts/run.py'])
def test_unsafe_paths_refused(tmp_path, name):
    with pytest.raises(ValueError):
        h.destination(tmp_path, name)


def test_case_collision_refused():
    with pytest.raises(ValueError, match='colliding'):
        h.records({'files': [{'path': 'data/X'}, {'path': 'data/x'}]})


def test_secret_file_blocks_publication(pair):
    a, b, shared = pair
    (a / 'data/.env').write_text('local setting')
    with pytest.raises(ValueError, match='Private settings'):
        h.publish(a, shared, {})


def test_interrupted_receive_resumes_without_losing_original(pair, monkeypatch):
    a, b, shared = pair
    name = 'review/current/answers.csv'
    old = (b / name).read_bytes()
    (a / name).write_text('Reviewed answer')
    (a / 'data/raw/new.txt').write_text('New evidence')
    m = h.publish(a, shared, {})
    replace = h.os.replace
    def fail_state_once(src, dst):
        if Path(dst) == h.state_path(b):
            raise OSError('Simulated interrupted receipt write')
        return replace(src, dst)
    monkeypatch.setattr(h.os, 'replace', fail_state_once)
    with pytest.raises(OSError, match='interrupted'):
        h.receive(b, shared)
    assert json.loads(h.state_path(b).read_text())['id'] == 'baseline'
    monkeypatch.setattr(h.os, 'replace', replace)
    h.receive(b, shared)
    assert (b / name).read_text() == 'Reviewed answer'
    assert (b / '.workspace-local/handoff/recovery' / m['id'] / name).read_bytes() == old
    assert (b / 'data/raw/new.txt').read_text() == 'New evidence'


def test_new_local_edit_after_interruption_is_not_overwritten(pair, monkeypatch):
    a, b, shared = pair
    (a / 'data/raw/new.txt').write_text('Incoming')
    h.publish(a, shared, {})
    replace = h.os.replace
    def fail_state(src, dst):
        if Path(dst) == h.state_path(b):
            raise OSError('Interrupted state write')
        return replace(src, dst)
    monkeypatch.setattr(h.os, 'replace', fail_state)
    with pytest.raises(OSError):
        h.receive(b, shared)
    monkeypatch.setattr(h.os, 'replace', replace)
    (b / 'data/raw/new.txt').write_text('Local edit after interruption')
    with pytest.raises(ValueError, match='replace local work'):
        h.receive(b, shared)
    assert (b / 'data/raw/new.txt').read_text() == 'Local edit after interruption'


def test_verified_archived_database_is_allowed_but_not_changed(pair):
    import sqlite3
    import shutil
    a, b, shared = pair
    database = a / 'data/raw/archive.sqlite'
    with sqlite3.connect(database) as con:
        con.execute('create table evidence (id integer)')
    shutil.copy2(database, b / 'data/raw/archive.sqlite')
    folder, m = h.load_snapshot(shared, 'baseline')
    m['files'].append({'path': 'data/raw/archive.sqlite', 'bytes': database.stat().st_size, 'sha256': h.digest(database)})
    h.atomic_json(folder / 'manifest.json', m)
    h.atomic_json(shared / 'latest.json', {'id': 'baseline', 'sha256': h.digest(folder / 'manifest.json')})
    for root in [a, b]:
        h.state_path(root).unlink()
        h.initialize(root, shared)
    h.publish(a, shared, {})
    h.receive(b, shared)
    sidecar = Path(str(database) + '-wal')
    sidecar.write_bytes(b'pending journal')
    with pytest.raises(ValueError, match='live database'):
        h.publish(a, shared, {})
    sidecar.unlink()
    with sqlite3.connect(database) as con:
        con.execute('insert into evidence values (1)')
    with pytest.raises(ValueError, match='Archived database changed'):
        h.publish(a, shared, {})


def test_new_database_requires_separate_snapshot(pair):
    a, b, shared = pair
    (a / 'data/raw/new.sqlite').write_bytes(b'new database')
    with pytest.raises(ValueError, match='Private settings or live database'):
        h.publish(a, shared, {})

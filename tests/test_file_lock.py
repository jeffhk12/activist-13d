"""Pin cross-process lock exclusion and release without a live research run.

Inputs: temporary lock and child process. Outputs: contention/release assertions.
Identity: locked -> contender exit 2; released/closed -> contender exit 0.
Tier: 1. Run: project .venv/bin/python -m pytest tests/test_file_lock.py.
"""
import os
import subprocess
import sys
from pathlib import Path

from activist13d.file_lock import acquire_exclusive, release


def test_process_exclusion_and_release(tmp_path):
    child = tmp_path / 'contender.py'
    child.write_text('''from pathlib import Path
import sys
from activist13d.file_lock import acquire_exclusive
with Path(sys.argv[1]).open('a+') as handle:
    try:
        acquire_exclusive(handle)
    except BlockingIOError:
        sys.exit(2)
''', encoding='utf-8')
    path = tmp_path / 'worker.lock'
    env = {**os.environ, 'PYTHONPATH': str(Path(__file__).parents[1] / 'src')}

    def contender():
        return subprocess.run([sys.executable, str(child), str(path)], env=env,
                              capture_output=True, text=True).returncode

    with path.open('a+') as handle:
        acquire_exclusive(handle)
        assert contender() == 2
        release(handle)
        assert contender() == 0
        acquire_exclusive(handle)
        assert contender() == 2
    assert contender() == 0

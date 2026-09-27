"""Pin portable pilot report bytes under Windows text-file newline translation.

Inputs: empty synthetic report. Output: newline assertion. Tier: 1.
Identity: saved report line endings are LF on every operating system.
Run: project .venv/bin/python -m pytest tests/test_workspace_portability.py.
"""
import importlib.util
import sys
from pathlib import Path


def test_pilot_report_bytes_are_portable(tmp_path, monkeypatch):
    script = Path(__file__).parents[1] / 'scripts/collect_pilot.py'
    spec = importlib.util.spec_from_file_location('portable_pilot', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = tmp_path

    def windows_write(path, data, encoding=None, errors=None, newline=None):
        with path.open('w', encoding=encoding, errors=errors,
                       newline='\r\n' if newline is None else newline) as stream:
            return stream.write(data)

    monkeypatch.setattr(Path, 'write_text', windows_write)
    module.write_review([], dict(n=0, item4_found=0, roles_found=0,
                                 cusip_found=0, event_date_found=0))
    report = (tmp_path / 'research/runs/SEC-PILOT-REPORT.md').read_bytes()
    assert b'\n' in report
    assert b'\r\n' not in report


def test_sec_collector_imports_without_unix_fcntl(monkeypatch):
    monkeypatch.setitem(sys.modules, 'fcntl', None)
    script = Path(__file__).parents[1] / 'scripts/data_collection/sec_bulk.py'
    spec = importlib.util.spec_from_file_location('windows_sec_bulk', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

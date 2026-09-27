"""Offline date, security-class and ambiguous-link refusal pins."""
from phase1_event_feasibility import entry_proxy, match_security, positive, security_screen


def test_exchange_calendar_holiday_and_replay():
    import exchange_calendars
    calendar = exchange_calendars.get_calendar('XNYS', start='2025-01-01', end='2025-01-15')
    sessions = [s.date().isoformat() for s in calendar.sessions]
    assert '2025-01-09' not in sessions  # Carter national day of mourning.
    assert entry_proxy('2025-01-08T18:00:00', sessions) == '2025-01-13'
    assert entry_proxy('2025-01-08T18:00:00', sessions) == entry_proxy('2025-01-08T18:00:00', list(sessions))


def evidence(permno=1, **updates):
    row = dict(permno=permno, namedt='2025-01-01', nameenddt='2025-12-31',
               securitytype='EQTY', securitysubtype='COM', sharetype='NS',
               issuertype='CORP', usincflg='Y')
    row.update(updates)
    return {'row': row, 'source': 'synthetic', 'result_index': 0}


def test_historical_bounds_and_no_header_fallback():
    index = {'12345678': [evidence()]}
    assert match_security('123456789', '2025-01-01', index)['permno'] == 1
    assert match_security('12345678', '2025-12-31', index)['permno'] == 1
    assert match_security('12345678', '2026-01-01', index)['permno'] is None
    assert match_security(None, '2025-01-01', index)['permno'] is None
    assert match_security('87654321', '2025-01-01', index)['permno'] is None


def test_ambiguous_security_and_code_conflict():
    assert match_security('12345678', '2025-01-01', {'12345678': [evidence(1), evidence(2)]})['status'] == 'ambiguous_permno'
    link = match_security('12345678', '2025-01-01', {'12345678': [evidence(1), evidence(1, securitytype='FUND')]})
    assert security_screen(link) == 'conflicting_security_codes'


def test_fund_not_corporate_even_when_issuer_is_corporation():
    link = {'permno': 1, 'evidence': [evidence(securitytype='FUND', securitysubtype='CEF', issuertype='ACOR')]}
    assert security_screen(link) == 'fund_vehicle_separate_review'
    assert security_screen({'permno': 1, 'evidence': [evidence()]}) == 'corporate_common_candidate'
    assert security_screen({'permno': 1, 'evidence': [evidence(sharetype='AD')]}) == 'other_security_separate_review'


def test_full_session_delay_and_end_of_calendar_refusal():
    sessions = ['2025-01-03', '2025-01-06', '2025-01-07', '2025-01-08']
    # Friday filing: Monday is the full waiting session, Tuesday is entry proxy.
    assert entry_proxy('2025-01-03T16:30:00', sessions) == '2025-01-07'
    assert entry_proxy('2025-01-04T12:00:00', sessions) == '2025-01-07'
    assert entry_proxy('2025-01-07T12:00:00', sessions) is None
    assert entry_proxy(None, sessions) is None
    assert positive('12.5') and not positive('-12.5') and not positive('NaN')


def test_vendor_page_hash_refusal_and_replay(tmp_path):
    import gzip
    import hashlib
    import json

    import phase1_event_feasibility as module
    import pytest

    root = tmp_path / 'crsp.stocknames_v2'
    root.mkdir()
    path = root / 'sample.json.gz'
    raw = b'{"results": [{"permno": 1}]}'
    path.write_bytes(gzip.compress(raw))
    meta = {'sha256': hashlib.sha256(raw).hexdigest(), 'raw_bytes': len(raw),
            'request': {'url': 'https://example.test/crsp.stocknames_v2/'}}
    path.with_suffix('.meta.json').write_text(json.dumps(meta))
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, 'ROOT', tmp_path)
        first, inventory = {}, {}
        a = module.read_page(path, first)
        b = module.read_page(path, inventory)
        assert a == b and first == inventory
        assert a[0]['results'] == [{'permno': 1}]
        path.write_bytes(gzip.compress(b'{"results": []}'))
        with pytest.raises(AssertionError):
            module.read_page(path, {})

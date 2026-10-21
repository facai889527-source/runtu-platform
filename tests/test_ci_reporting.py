import subprocess

import pytest

from scripts.ci_tests import run_tests


@pytest.mark.parametrize('output,exit_code,expected', [
    ('5 passed in 1s', 0, 0),
    ('4 passed, 1 skipped in 1s', 0, 2),
    ('5 skipped in 1s', 0, 2),
    ('4 passed, 1 failed in 1s', 1, 1),
    ('0 passed in 1s', 0, 2),
])
def test_online_count_is_exact_and_cannot_pass_with_skips(monkeypatch, output, exit_code, expected):
    monkeypatch.setattr('scripts.ci_tests.subprocess.run', lambda *_, **__: subprocess.CompletedProcess([], exit_code, output, ''))
    assert run_tests(['tests/postgres'], expected_passed=5) == expected


def test_reporter_prints_only_counts_and_failure_locations(monkeypatch, capsys):
    secret = 'disposable-session-do-not-emit'
    output = 'tests/postgres/test_integration.py:100: AssertionError\nFAILED tests/postgres/test_integration.py::test_auth - token=' + secret + '\n1 failed in 1s'
    monkeypatch.setattr('scripts.ci_tests.subprocess.run', lambda *_, **__: subprocess.CompletedProcess([], 1, output, secret))
    assert run_tests(['tests/postgres'], expected_passed=5) == 1
    report = capsys.readouterr()
    assert secret not in report.out + report.err
    assert 'test_integration.py:100' in report.out

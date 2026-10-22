"""Run pytest with count assertions and credential-safe console reporting."""
import re
import subprocess
import sys


def run_tests(paths, *, environment=None, expected_passed=None, expected_skipped=0, timeout=180):
    try:
        result = subprocess.run([sys.executable, '-m', 'pytest', '-q', *paths, '--tb=short', '--show-capture=no'],
            env=environment, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        print('pytest did not finish; raw diagnostics suppressed')
        return 2
    # Only integers, known outcome labels and source locations are emitted.
    counts = {key: 0 for key in ('passed', 'failed', 'skipped', 'error')}
    for count, label in re.findall(r'\b(\d+) (passed|failed|skipped|errors?)\b', result.stdout):
        counts[label.rstrip('s') if label.startswith('error') else label] = int(count)
    print('pytest counts: ' + ', '.join(f'{key}={value}' for key, value in counts.items()))
    for location in sorted(set(re.findall(r'(?m)^(tests/[A-Za-z0-9_./]+\.py:\d+):', result.stdout))):
        print('Failure location: ' + location)
    for case in re.findall(r'^FAILED (tests/[A-Za-z0-9_./]+::test_[A-Za-z0-9_]+)', result.stdout, re.MULTILINE):
        print('Failed case: ' + case)
    if (result.returncode or counts['failed'] or counts['error'] or counts['passed'] == 0
            or counts['skipped'] != expected_skipped
            or (expected_passed is not None and counts['passed'] != expected_passed)):
        return result.returncode or 2
    return 0


if __name__ == '__main__':
    # Full unit suite includes eleven deliberately opt-in online tests, validated separately.
    raise SystemExit(run_tests(['tests'], expected_skipped=11))

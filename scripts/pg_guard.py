"""Guards for an exclusively runner-created, disposable PostgreSQL container."""
import json
import os
import re
import shutil
import subprocess

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

LABEL = 'runtu.pg-validation'


class GuardRefused(RuntimeError):
    pass


def docker_command(arguments, *, endpoint=None, environment=None, timeout=20):
    binary = shutil.which('docker')
    if not binary:
        raise GuardRefused('Docker unavailable; no PostgreSQL online validation performed')
    command = [binary] + (['--host', endpoint] if endpoint else []) + list(arguments)
    try:
        result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise GuardRefused('Docker command failed; output suppressed') from None
    if result.returncode:
        raise GuardRefused('Docker command refused or unavailable; output suppressed')
    return result.stdout.strip()


def local_endpoint(value):
    if not isinstance(value, str) or not value.startswith(('unix:///', 'npipe:////./pipe/')) or any(c in value for c in '\r\n'):
        raise GuardRefused('Only a local Docker socket is permitted')
    return value


def validate_target(dsn, run_id, info):
    """Pure validation before any SQL connection or destructive action."""
    try:
        if not re.fullmatch(r'[0-9a-f]{32}', run_id):
            raise ValueError
        url = make_url(dsn)
        expected = 'runtu_test_' + run_id
        ports = info['NetworkSettings']['Ports']['5432/tcp']
        if (url.drivername != 'postgresql+psycopg' or url.host != '127.0.0.1'
            or url.database != expected or url.username != expected or url.query
            or not url.password or len(url.password) < 32 or not url.port
            or info['Config']['Labels'].get(LABEL) != run_id
            or info['Name'] != '/runtu-pg-' + run_id
            or not info['State']['Running'] or len(ports) != 1
            or ports[0]['HostIp'] != '127.0.0.1' or int(ports[0]['HostPort']) != url.port
            or not any(m.get('Type') == 'tmpfs' and m.get('Destination') == '/var/lib/postgresql/data' for m in info['Mounts'])
            or any(m.get('Type') == 'bind' for m in info['Mounts'])):
            raise ValueError
        return url
    except (KeyError, TypeError, ValueError, AttributeError, ArgumentError):
        raise GuardRefused('Disposable PostgreSQL target guard refused') from None


def inspect_owned(endpoint, container, run_id):
    if not re.fullmatch(r'[0-9a-f]{64}', container):
        raise GuardRefused('Invalid container identity')
    try:
        info = json.loads(docker_command(['inspect', container], endpoint=local_endpoint(endpoint)))[0]
        if (info['Id'] != container or info['Config']['Labels'].get(LABEL) != run_id
                or info['Name'] != '/runtu-pg-' + run_id):
            raise ValueError
        return info
    except (KeyError, IndexError, TypeError, ValueError):
        raise GuardRefused('Container ownership check refused; nothing removed') from None


def guarded_test_url(environment=None):
    env = os.environ if environment is None else environment
    try:
        run_id, container = env['RUNTU_PG_TEST_RUN_ID'], env['RUNTU_PG_TEST_CONTAINER']
        endpoint = local_endpoint(env['RUNTU_PG_TEST_ENDPOINT'])
        return validate_target(env['RUNTU_PG_TEST_DSN'], run_id, inspect_owned(endpoint, container, run_id))
    except KeyError:
        raise GuardRefused('Use the disposable container runner; external DSNs are not accepted') from None

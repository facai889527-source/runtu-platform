"""Optional local Docker-only PG suite. Never accepts an existing database DSN."""
import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time

from sqlalchemy.engine import URL

from scripts.pg_guard import LABEL, GuardRefused, docker_command, inspect_owned, local_endpoint, validate_target
from scripts.ci_tests import run_tests


class SafeParser(argparse.ArgumentParser):
    def error(self, _message):
        self.print_usage(sys.stderr)
        self.exit(2, 'Invalid arguments; external DSNs are not accepted. Argument values suppressed.\n')


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--image', default='postgres:17', help='Previously reviewed, locally available official PostgreSQL 17 image')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'(?:docker.io/library/)?postgres(?::17(?:\.[0-9]+)?(?:-bookworm)?|@sha256:[0-9a-f]{64})', args.image):
        print('Refused: use a reviewed PostgreSQL 17 official image reference', file=sys.stderr)
        return 2
    endpoint = container = None
    run_id = secrets.token_hex(16)
    name = 'runtu-pg-' + run_id
    environment = {k: v for k, v in os.environ.items() if not k.startswith(('RUNTU_', 'PG', 'POSTGRES_'))}
    result_code = 2
    try:
        if os.environ.get('DOCKER_HOST') or os.environ.get('DOCKER_CONTEXT'):
            raise GuardRefused('Unset Docker environment overrides; only the inspected local context is permitted')
        endpoint = local_endpoint(json.loads(docker_command(['context', 'inspect', '--format', '{{json .Endpoints.docker.Host}}'])))
        version = docker_command(['version', '--format', '{{.Server.Version}}'], endpoint=endpoint)
        if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?', version) or int(version.split('.')[0]) < 28:
            raise GuardRefused('Docker Engine 28+ required for loopback publication safety')
        # No pull, packages, service installation or daemon configuration changes.
        image_id = docker_command(['image', 'inspect', args.image, '--format', '{{.Id}}'], endpoint=endpoint)
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', image_id):
            raise GuardRefused('Image identity unavailable')
        print('Docker Engine: ' + version + '; local image ID: ' + image_id)
        database = 'runtu_test_' + run_id
        environment.update(POSTGRES_USER=database, POSTGRES_DB=database,
                           POSTGRES_PASSWORD=secrets.token_urlsafe(40), POSTGRES_INITDB_ARGS='--auth-host=scram-sha-256')
        # Create first, so cleanup has an exact ID even if startup fails.
        container = docker_command(['create', '--name', name, '--label', LABEL + '=' + run_id,
            '--publish', '127.0.0.1::5432', '--mount', 'type=tmpfs,destination=/var/lib/postgresql/data',
            '--env', 'POSTGRES_USER', '--env', 'POSTGRES_DB', '--env', 'POSTGRES_PASSWORD',
            '--env', 'POSTGRES_INITDB_ARGS', '--memory', '512m', '--cpus', '2', image_id],
            endpoint=endpoint, environment=environment)
        inspect_owned(endpoint, container, run_id)
        print('Owned test container: ' + name)
        docker_command(['start', container], endpoint=endpoint)
        for _ in range(60):
            try:
                docker_command(['exec', container, 'pg_isready', '-q', '-h', '127.0.0.1', '-U', database, '-d', database], endpoint=endpoint)
                break
            except GuardRefused:
                time.sleep(0.5)
        else:
            raise GuardRefused('Disposable PG did not become ready; no database tests run')
        info = inspect_owned(endpoint, container, run_id)
        ports = info['NetworkSettings']['Ports']['5432/tcp']
        port = int(ports[0]['HostPort'])
        url = URL.create('postgresql+psycopg', username=database, password=environment['POSTGRES_PASSWORD'],
                         host='127.0.0.1', port=port, database=database)
        dsn = url.render_as_string(hide_password=False)
        validate_target(dsn, run_id, info)
        pg_version = docker_command(['exec', container, 'postgres', '--version'], endpoint=endpoint)
        if not re.fullmatch(r'postgres \(PostgreSQL\) 17\.[0-9]+(?: \([A-Za-z0-9.+~ -]+\))?', pg_version):
            raise GuardRefused('Expected PostgreSQL 17; version output suppressed')
        print('Disposable online environment: ' + pg_version)
        environment.update(RUNTU_PG_TEST_DSN=dsn, RUNTU_PG_TEST_RUN_ID=run_id,
                           RUNTU_PG_TEST_CONTAINER=container, RUNTU_PG_TEST_ENDPOINT=endpoint)
        # Nine must execute; no skips, traceback, requests or raw DB diagnostics are emitted.
        result_code = run_tests(['tests/postgres'], environment=environment, expected_passed=9)
    except GuardRefused as failure:
        print('PG online validation blocked: ' + str(failure), file=sys.stderr)
    except (ValueError, KeyError, IndexError, subprocess.TimeoutExpired):
        print('PG online validation blocked or failed. Check local Docker 28+, reviewed local image and documented guards. No secret diagnostics emitted.', file=sys.stderr)
    finally:
        if container and endpoint:
            try:
                inspect_owned(endpoint, container, run_id)
                docker_command(['rm', '--force', '--volumes', container], endpoint=endpoint)
                print('Owned disposable PostgreSQL container removed.')
            except GuardRefused:
                result_code = 2
                print('Cleanup refused/failed: inspect only the runtu.pg-validation labelled test container; no unrelated resources were removed.', file=sys.stderr)
    return result_code


if __name__ == '__main__':
    raise SystemExit(main())

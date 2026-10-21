from copy import deepcopy

import pytest
from sqlalchemy.engine import URL

from scripts.pg_guard import GuardRefused, LABEL, guarded_test_url, inspect_owned, local_endpoint, validate_target
from scripts.test_postgres import main

RUN = 'a' * 32


def target():
    name = 'runtu_test_' + RUN
    url = URL.create('postgresql+psycopg', username=name, password='test-only-' * 5,
                     host='127.0.0.1', port=54321, database=name)
    info = {'Name': '/runtu-pg-' + RUN, 'Config': {'Labels': {LABEL: RUN}}, 'State': {'Running': True},
            'NetworkSettings': {'Ports': {'5432/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '54321'}]}},
            'Mounts': [{'Type': 'tmpfs', 'Destination': '/var/lib/postgresql/data'}]}
    return url, info


def test_guard_accepts_only_explicit_owned_test_identity():
    url, info = target()
    assert validate_target(url.render_as_string(hide_password=False), RUN, info) == url


@pytest.mark.parametrize('change', [
    {'host': 'db.example'}, {'host': 'localhost'}, {'database': 'postgres'}, {'database': 'production'},
    {'username': 'postgres'}, {'drivername': 'sqlite'}, {'password': ''},
    {'port': 54322}, {'query': {'host': 'production'}},
])
def test_guard_rejects_wrong_or_default_dsn_without_connection(change):
    url, info = target()
    with pytest.raises(GuardRefused, match='guard refused'):
        validate_target(url.set(**change).render_as_string(hide_password=False), RUN, info)


@pytest.mark.parametrize('change', ['label', 'name', 'public', 'stopped', 'bind', 'persistent'])
def test_guard_rejects_unowned_or_exposed_container(change):
    url, original = target()
    info = deepcopy(original)
    if change == 'label': info['Config']['Labels'][LABEL] = 'other'
    elif change == 'name': info['Name'] = '/not-owned'
    elif change == 'public': info['NetworkSettings']['Ports']['5432/tcp'][0]['HostIp'] = '0.0.0.0'
    elif change == 'stopped': info['State']['Running'] = False
    elif change == 'bind': info['Mounts'].append({'Type': 'bind', 'Destination': '/anything'})
    elif change == 'persistent': info['Mounts'] = [{'Type': 'volume', 'Destination': '/var/lib/postgresql/data'}]
    with pytest.raises(GuardRefused):
        validate_target(url.render_as_string(hide_password=False), RUN, info)


@pytest.mark.parametrize('endpoint', ['tcp://127.0.0.1:2375', 'ssh://remote', 'http://localhost', 'npipe:////remote/pipe/docker', ''])
def test_remote_docker_endpoints_rejected(endpoint):
    with pytest.raises(GuardRefused):
        local_endpoint(endpoint)


def test_missing_docker_fails_before_database_connection(monkeypatch, capsys):
    monkeypatch.delenv('DOCKER_HOST', raising=False)
    monkeypatch.delenv('DOCKER_CONTEXT', raising=False)
    monkeypatch.setattr('scripts.pg_guard.shutil.which', lambda _: None)
    assert main([]) == 2
    result = capsys.readouterr()
    assert 'Docker unavailable' in result.err
    assert 'postgresql://' not in result.out + result.err


def test_default_or_malformed_database_configuration_is_never_used():
    with pytest.raises(GuardRefused):
        guarded_test_url({'RUNTU_DATABASE_URL': 'postgresql://production.invalid/default'})
    _, info = target()
    with pytest.raises(GuardRefused):
        validate_target('malformed connection string', RUN, info)


def test_cleanup_ownership_mismatch_refuses_before_any_remove(monkeypatch):
    import json
    _, info = target()
    info['Id'] = 'b' * 64
    info['Config']['Labels'][LABEL] = 'another-run'
    calls = []
    def fake_docker(arguments, **_):
        calls.append(arguments)
        return json.dumps([info])
    monkeypatch.setattr('scripts.pg_guard.docker_command', fake_docker)
    with pytest.raises(GuardRefused, match='ownership check refused'):
        inspect_owned('unix:///var/run/docker.sock', 'b' * 64, RUN)
    assert calls == [['inspect', 'b' * 64]]


def test_rejected_cli_arguments_do_not_echo_credentials(capsys):
    secret = 'disposable-password-must-not-print'
    with pytest.raises(SystemExit) as result:
        main(['--dsn', 'postgresql://operator:' + secret + '@localhost/production'])
    assert result.value.code == 2
    output = capsys.readouterr()
    assert secret not in output.out + output.err

"""Explicit disposable loopback fixture for the Chrome auth smoke test; not deployment."""
from pathlib import Path
import json
import secrets
import sys

import uvicorn

from backend.app import create_app
from backend.config import Settings
from backend.migrations import migrate_database


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / '.git' / 'codex-coordination' / 'auth14'
    output.mkdir(parents=True, exist_ok=True)
    # Unique DB and credentials; never reuse an operator or production account.
    db_path = output / f'browser-{secrets.token_hex(8)}.db'
    credentials = output / 'browser-credentials.json'
    app = create_app(Settings(_env_file=None, database_url=f'sqlite:///{db_path.as_posix()}',
        auth_origin='http://127.0.0.1:5173', auth_allow_loopback_http=True))
    migrate_database(app.state.database)
    password = secrets.token_urlsafe(32)
    app.state.auth_service.bootstrap('browser-test', password)
    # Exclusive creation refuses to overwrite an existing test's credentials.
    owns_credentials = False
    try:
        with credentials.open('x', encoding='utf-8') as stream:
            owns_credentials = True
            json.dump({'username': 'browser-test', 'password': password}, stream)
        print('Disposable auth fixture ready on loopback; access logging disabled.')
        uvicorn.run(app, host='127.0.0.1', port=8000, access_log=False, proxy_headers=False)
    finally:
        app.state.database.dispose()
        if owns_credentials:
            credentials.unlink(missing_ok=True)
        db_path.unlink(missing_ok=True)


if __name__ == '__main__':
    sys.exit(main())

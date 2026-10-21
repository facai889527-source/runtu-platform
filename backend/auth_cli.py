"""Local interactive bootstrap and explicit session cleanup. Never an HTTP endpoint."""
import argparse
import getpass
import sys
import warnings

from backend.auth.service import AuthService, AuthUnavailable, BootstrapRefused
from backend.config import Settings
from backend.database import Database


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['bootstrap-admin', 'cleanup-sessions'])
    args = parser.parse_args(argv)
    database = None
    try:
        settings = Settings()
        if settings.database_url is None:
            raise AuthUnavailable('Database required; migrate explicitly first')
        database = Database(settings.database_url.get_secret_value())
        service = AuthService(database, settings)
        if args.command == 'bootstrap-admin':
            if not sys.stdin.isatty():
                raise BootstrapRefused('Interactive terminal required')
            username = input('Administrator username: ')
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                password = getpass.getpass('Password (14-128 characters): ')
                confirmation = getpass.getpass('Confirm password: ')
            if password != confirmation:
                raise BootstrapRefused('Passwords do not match')
            service.bootstrap(username, password)
            print('Administrator created. No session was issued.')
        else:
            print(f'Expired sessions removed: {service.cleanup()}')
        return 0
    except (AuthUnavailable, BootstrapRefused, ValueError, EOFError, getpass.GetPassWarning):
        print('Operation refused. Check local configuration, migration and bootstrap state.', file=sys.stderr)
        return 1
    finally:
        if database:
            database.dispose()


if __name__ == '__main__':
    raise SystemExit(main())

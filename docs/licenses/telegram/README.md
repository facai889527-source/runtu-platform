# Telegram secret storage dependency notices

cryptography 50.0.2 is pinned in backend/requirements.txt for authenticated Fernet/MultiFernet encryption. The installed distribution's LICENSE, LICENSE.APACHE and LICENSE.BSD are retained here. Existing cffi 2.0.0 and pycparser 2.23 notices remain in ../auth. No encryption key is distributed or generated during application startup.

Upstream: https://github.com/pyca/cryptography/tree/50.0.2 and https://cryptography.io/en/stable/fernet/. Operator-managed keys and rotation are documented in ../../TELEGRAM_SECURITY_MILESTONE.md.

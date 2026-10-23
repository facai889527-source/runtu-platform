# TASK-0052: security foundation milestone (partial delivery)

Historical TASK-0052 boundary. TASK-0053 subsequently adds explicit public-bot choice, private target opt-in and owner management; see [current notification behavior](NOTIFICATIONS.md). TASK-0054 subsequently integrates personal Bot encrypted persistence, private proof and rotation; group/multi-target integration remains unfinished. See the current notification guide for operational prerequisites.

This is a bounded foundation milestone, **not completion of TASK-0052**. No new notification endpoints, personal bot binding, group discovery, owner cross-account controls, multi-target routing, UI, or migration are activated by this change. Existing TASK-0051 behavior remains; it must not be presented as satisfying TASK-0052. Unfinished integration drafts are excluded from the PR. No real database, Telegram credentials, service restart, or delivery was used for validation.

## Delivered boundary

`backend.telegram_security.TelegramVault` encrypts a token inside an authenticated account-ID envelope using Fernet. Decryption checks the account ID, so copying ciphertext between account rows fails closed. Missing/invalid operator keys, tampering, unknown keys, and malformed authenticated envelopes raise a generic exception. Secrets are returned internally as Pydantic SecretStr only; this is not an API serialization policy or an authorization layer. Future callers must enforce owner/self authorization, validate token input, and exclude secrets from all response and audit schemas.

`RUNTU_NOTIFICATION_ENCRYPTION_KEYS` is an optional SecretStr setting, containing one to four comma-separated Fernet keys, newest first, without whitespace. It is unused by current notification routes. Provision keys through operator-controlled secret storage, separately from database backups; never commit keys or put them in browser configuration. The application does not generate a key on startup. Loss of all decrypting keys makes stored ciphertext unrecoverable.

For future integration, add a new operator-managed key first while retaining the old keys; invoke vault rotation in an authorized transaction for each account; verify all rows decrypt with the new key before retiring old keys. MultiFernet preserves the authenticated token timestamp during rotation. This milestone provides the primitive and tests, not a batch rotation command, secret-management UI, or database storage integration. Do not remove an old key merely because one unit test passed.

`TelegramAPI` uses a fixed certificate-verified HTTPS host, a fixed method allowlist, token path validation, JSON POST bodies capped at 64 KiB, response reads capped at 64 KiB plus one detection byte, and a two-second socket timeout. It does not follow redirects, use environment proxies, or expose upstream descriptions/transport errors. HTTP 409 becomes a generic busy error. Cleanup failures cannot reveal credential-bearing URLs. The socket timeout is **not an end-to-end deadline**; future orchestration needs queue bounds, cancellation/deadline and rate controls. This client is not wired into existing delivery code.

## Remaining acceptance scope

- Pristine unbound state for all accounts, explicit public/personal choice, migration/reset policy and complete disconnect cleanup.
- Encrypted personal-bot persistence, getMe control checks, secure owner-only cross-account configuration and rotation operations; admins/users remain self-only.
- Private one-time handshake for each selected bot; discovery of bot-visible updates with committed offsets and uniquely owned polling leases; explicit exclusive-deployment acknowledgement and refusal of existing webhooks/409 conflicts. Telegram cannot enumerate historical groups or prove the absence of an external poller.
- Public-group visibility intersection with verified current user membership; owner full discovered-group view. Verify returned identities, bot membership/send permissions, selection and dispatch authorization, and revocation/race handling.
- Multiple private/group targets, per-event/per-account/per-destination durable dedupe, bounded queues and total deadlines, current permissions and event opt-in checks.
- Accessible responsive choice/discovery/target UI, owner management, mocked integration and responsive browser tests, isolated migrations and PostgreSQL validation of new schema.

A formal follow-up task/version should carry the remaining scope. The current signal must not automatically replay a partial/failed version. PR28 remains stacked on PR27; neither is merged or deployed by this milestone.

## Validation

Twenty isolated security tests cover owner-bound encryption, tampering, key rotation/removal, missing/invalid key storage, malformed authenticated envelopes, fixed host/method, redirects, conflict, malformed/oversized responses, credential path injection, oversized/non-finite requests, and sanitized connection/cleanup errors. They use in-memory generated keys and mocked HTTP only. Full repository regression and CI results are recorded in PR28 and the coordination status; none constitutes real Telegram acceptance.

References: [Fernet / MultiFernet](https://cryptography.io/en/stable/fernet/), [Telegram getUpdates](https://core.telegram.org/bots/api#getupdates), [getChatMember](https://core.telegram.org/bots/api#getchatmember), [deep links](https://core.telegram.org/bots/features#deep-linking). Dependency notices are retained in [licenses/telegram](licenses/telegram/README.md).

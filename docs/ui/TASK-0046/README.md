# TASK-0046 personalized home

The home keeps its topbar title and four-item role-aware sidebar. The first viewport now identifies the current account with a restrained greeting, localized role, enabled status and exact number of enabled authorized tools. A dedicated security card shows only the previous successful login, with server UTC converted to browser-local time. Public demos remain separate from personal grants. Tool shortcuts are functional existing routes; no recent-use tracking, invented statistics or personal-settings route is added. System diagnostics are compact and owner-only.

Empty personal tools use one concise message. Many tools use a responsive grid; the count is computed only after all bounded own-tool pages load, and stays unknown while loading/failing. The login-history error state is distinct from “暂无记录”; a known time with unknown IP shows “未记录”. Long names retain accessible full text/title while using a compact visual ellipsis. Visual review covered all target widths and revised the long-name greeting after the first screenshot pass.

## Schema and operation boundary

**Local upgrade required: `0007_login_activity` has not been applied to the real development SQLite database.** No running service was restarted. Current old backend cannot serve the new history endpoint; the UI shows unavailable rather than inventing history. Real history acceptance requires separate authorization for the reviewed upgrade and backend enablement; do not bootstrap or reset an account to get records.

The migration reuses `auth_events` with a nullable successful source IP, plus a per-user last-event pointer and per-session previous-event pointer. Successful audit/session rotation/pointer advance are transactional. Existing successful timestamps are reused; hashed legacy IPs are never reconstructed. Strict legacy session time boundaries avoid labeling current login as previous. New sessions snapshot event references, including equal timestamps and concurrent pointer protection. No duplicate audit table is added.

Only the current valid user can read `/api/auth/activity`; user query parameters are rejected, references are checked against that user, and responses are no-store. Only a valid ASGI connection address can be recorded. Forwarded/real-IP headers, hostnames and scoped addresses yield unknown IP rather than trusting arbitrary proxy data. Read the [authentication security details](../../AUTH_SECURITY.md#task-0046当前账户的上次成功登录) before deployment. Original user passwords, role/status and session identifiers are not changed by the migration.

## Screenshots

All images use synthetic fixture accounts, reserved documentation IPs and intercepted APIs, never real user/session/database data. Views are exact 1440×900, 390×844 and 360×800 captures.

| Case | Desktop | Mobile | Narrow mobile |
| --- | --- | --- | --- |
| Owner, no history or tools | [1440](home-owner-empty-1440.png) | [390](home-owner-empty-390.png) | [360](home-owner-empty-360.png) |
| Owner, history and 26 tools | [1440](home-owner-history-many-1440.png) | [390](home-owner-history-many-390.png) | [360](home-owner-history-many-360.png) |
| Admin, history and 26 tools | [1440](home-admin-history-many-1440.png) | [390](home-admin-history-many-390.png) | [360](home-admin-history-many-360.png) |
| Viewer, no history or tools | [1440](home-viewer-empty-1440.png) | [390](home-viewer-empty-390.png) | [360](home-viewer-empty-360.png) |
| Long username | [1440](home-long-name-1440.png) | [390](home-long-name-390.png) | [360](home-long-name-360.png) |

## Validation

- Node 29 tests passed; Vite production build passed (77 modules).
- Python full suite: 153 passed, 11 optional PostgreSQL cases skipped locally, one existing Starlette/httpx deprecation warning. Focused auth/history checks also passed after final UTC normalization. Migrations were exercised only on disposable databases, including old data preservation, strict same-instant boundaries, per-user backfill and downgrade guard behavior.
- History tests cover owner/admin/viewer privacy, absent history, equal timestamps, separate session snapshots, failed login/rollback, forged cross-user references, IPv4/IPv6 and arbitrary forwarding headers.
- Full isolated browser regression passed at 1440/390/360. Focused `RUNTU_HOME_ONLY=1` mode adds owner/admin/viewer/anonymous home states, 0/26 tools, absent/known/unknown-IP history, service errors and long names. No horizontal overflow was observed.
- Existing PostgreSQL online test count remains 11; its authentication role/rotation case now also validates own history and privacy.

PR28 remains based on PR27; neither is automatically merged. No migration, live account operation, service restart, deployment or next-task dispatch occurred.

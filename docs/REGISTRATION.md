# Registration policy and approval boundary

TASK-0034 design: a singleton policy defaults to disabled registration and required
approval. Only a current active owner with `users.manage`, a valid session, trusted
origin and CSRF proof may change it. Revision checks prevent stale policy writes.
Public registration always creates viewer accounts without module grants or sessions.

Pending registrations are inactive users with a separate pending marker. Login and
existing authenticated APIs already reject inactive users. Generic user edits cannot
activate or promote a pending registration; a dedicated owner approval transaction
sets viewer/active and marks approval atomically with audit. Disabling approval in
policy applies only to future submissions, never activates existing pending users.
Duplicate names receive the same generic submission acknowledgement; no account lookup
or registration-status endpoint is exposed. No automatic login or password delivery.

Writes share the existing bootstrap singleton mutex and authentication rate-limit
storage. Anonymous signup requires an unexpired anonymous CSRF session, consumed in
the creation transaction. Policy is rechecked under the mutex; stale/revoked owner
sessions are checked again there. Hashing uses existing Argon2 settings and bounded
verification slots. Source/global/name buckets bound attempts, including duplicates.
Audit contains event kind, user ID and hashed source only, never request bodies.

Migration 0006 creates the policy singleton and pending-registration table, without
modifying existing user rows. Downgrade refuses while pending applications exist:
dropping pending markers could let old user editors bypass approval. Otherwise it
loses policy and approval history only. Back up and review before separately
authorizing a real migration; application startup never migrates. Missing storage
fails closed with 503. Health readiness does not prove registration schema readiness.

UI follows the existing teal/slate admin theme and system Chinese typography. Settings
owns the policy draft and submission; an independent approval list owns pagination,
confirmation and refresh. Registration is a separate auth-layout form with native
password input cleared on submit/unmount. Disabled and pending states are textual,
without suggesting that an account was necessarily created for a duplicate name.

This foundation does not provide email verification, CAPTCHA, password recovery,
rejection/deletion, notifications or distributed edge abuse protection. Pending users
reserve their username; operator approval requires independent identity verification.
The process-wide hashing limit is per worker; database buckets are shared. Rate-limit
records use the existing cleanup lifecycle. Public enablement is an owner decision.

User role/status editing now also requires the 0006 approval-marker table; missing
tables fail closed rather than allowing a pending-account bypass. Existing accounts
are not rewritten by upgrade, and ordinary authentication remains unchanged.

Validation includes temporary SQLite migration/model consistency, pending downgrade
refusal, default-off, owner/admin/viewer matrix, CSRF/origin/body limits, duplicate
and rate-limit behavior, anonymous-context consumption, policy changes during hashing,
concurrent creation/approval, stale policy revision, audit rollback and revoked owner
session checks. The owned PostgreSQL CI suite runs the HTTP registration contract,
concurrent policy changes, audit rollback, model check and downgrade/re-upgrade.
Chrome uses intercepted APIs only at 1440/390/360; captures below contain fixture
identities and no entered passwords.

![Owner policy and approval fixture](images/task-0034/registration-owner-fixture.png)
![Public acknowledgement fixture](images/task-0034/registration-pending-fixture.png)

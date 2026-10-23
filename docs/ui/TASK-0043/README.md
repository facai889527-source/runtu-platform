# TASK-0043 internal UI review

The internal UI now uses neutral slate surfaces, a white role-aware sidebar and restrained teal actions. The workbench prioritizes granted tools and an honest empty state, with public demo shortcuts and collapsed administrator diagnostics. Users start with the account list; creation and identifiers are disclosed on request. Registration switches remain explicit-save controls with unsaved/saved feedback.

This branch is stacked on PR #27 (`codex/TASK-0038-auth-design`, c8f1c3a). Its PR targets that branch so the review contains only TASK-0043. Review/integrate #27 first, then retarget this PR onto main after verifying the resulting diff. No automatic integration or deployment is configured.

## Screenshots

All images use isolated fixture accounts and intercepted API responses. No real account, password, database content or environment configuration is captured. Before images are the archived pre-redesign fixture captures (full-page where applicable); after images are exact viewport captures, 1440×900 and 390×844.

| Page | Before desktop / mobile | After desktop / mobile |
| --- | --- | --- |
| Workbench | [desktop](before/dashboard-1440.png) / [mobile](before/dashboard-390.png) | [desktop](after/dashboard-1440.png) / [mobile](after/dashboard-390.png) |
| Modules | [desktop](before/modules-1440.png) / [mobile](before/modules-390.png) | [desktop](after/modules-1440.png) / [mobile](after/modules-390.png) |
| Users | [desktop](before/users-1440.png) / [mobile](before/users-390.png) | [desktop](after/users-1440.png) / [mobile](after/users-390.png) |
| Settings | [desktop](before/settings-1440.png) / [mobile](before/settings-390.png) | [desktop](after/settings-1440.png) / [mobile](after/settings-390.png) |

Visual review covered all eight after images. A second pass removed stacked settings spacing, tightened mobile user controls into two columns, restored a visible account-details disclosure marker and corrected muted navigation contrast. The final captures have no horizontal overflow. Long user lists and approval content scroll vertically.

## Verification

- Node: 28 tests passed, including safe login return to `/tools`; text/state contrast pairs meet 4.5:1.
- Vite production build passed (70 modules).
- Isolated Chrome fixture regression passed at 1440, 390 and 360 widths: owner/admin/viewer/anonymous navigation, direct URL denials, cold login chunk boundary, session expiry and login return, grants, user creation/update/conflict, audit pagination, registration approval/error states, keyboard switch with no write before save, account Escape/focus and mobile drawer/desktop collapse.
- Existing backend RBAC, user management, module access, registration and audit tests: 64 passed, one existing Starlette/httpx deprecation warning. Tests use independent temporary SQLite databases. The sandbox initially prevented default temporary-directory creation; the successful run used a repository-local isolated test directory with approved execution.
- Existing backend/frontend listeners were preserved. No migration, seed, administrator bootstrap or real user/session/grant write was performed.

Reproduce browser checks from repository root with `node frontend/tests/layout-browser-smoke.mjs` against the existing loopback dev server. It requires Windows Chrome and an unused debug port 9229; it intercepts every API request before the page loads. Screenshots go to the ignored coordination directory and refuse captures containing filled password fields.

# TASK-0044 navigation follow-up

Current title/tools revision: [TASK-0045](../TASK-0045/README.md). The captures below are an archived iteration.

This revision updates the existing PR28 branch, still based on PR27. No competing UI PR is created. The upper-left sidebar is the single brand area: **Runtu / 多功能工具平台**. The topbar contains only the mobile navigation control and account/data actions. The redundant brand text, management divider and home introduction are removed.

The owner navigation is exactly **首页 → 我的工具 → 用户管理 → 全局设置**. Admins see 首页, 我的工具 and 全局设置; global settings shows only module administration. Viewers see 首页 and 我的工具. Owner account management, registration policy and approval remain owner-only. Unauthorized direct settings visits retain a clear denial message. Server RBAC is unchanged.

Module administration is discoverable through **全局设置 → 模块与工具 → 模块管理**. It uses the existing `/modules` route, preserving bookmarks, module detail links and login return. On module pages the global-settings navigation remains active for permitted administrators.

## Screenshots

All screenshots use fixture accounts and intercepted APIs. Exact viewport dimensions are 1440×900 and 390×844; no live account credentials or database content is involved. The previous visual iteration is archived under [TASK-0043](../TASK-0043/README.md).

| Page | Desktop | Mobile |
| --- | --- | --- |
| 首页 | [1440](dashboard-1440.png) | [390](dashboard-390.png) |
| Modules | [1440](modules-1440.png) | [390](modules-390.png) |
| Users | [1440](users-1440.png) | [390](users-390.png) |
| 全局设置 | [1440](settings-1440.png) | [390](settings-390.png) |

Visual review confirms the single brand hierarchy, compact four-item navigation, uncluttered topbar and readable settings entry at desktop/mobile widths. Long settings and account content continues to scroll vertically.

## Validation

Node: 28 tests passed, including home/settings route labels and safe tool return. Vite production build passed (70 modules). The isolated Windows Chrome fixture exercises owner/admin/viewer/anonymous boundaries, exact owner navigation order, removed labels, module discovery through settings, deep links, active states, grants, registration explicit save/approval, audit, mobile drawer, desktop collapse, account Escape/focus and keyboard switches. No backend/API/schema changes; no real database writes or service restart.

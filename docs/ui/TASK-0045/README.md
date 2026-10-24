# TASK-0045 unified tools and page titles

Current personalized home follow-up: [TASK-0046](../TASK-0046/README.md).

This update stays on PR28, based on PR27. Every authenticated page has one H1 in the white topbar. The redundant large content title/intro is removed; refresh and account actions stay on the right. Titles wrap within the remaining width on narrow screens.

Global settings contains an inline **工具管理** section with registered tool names, versions, state, search/filter, detail/configuration links and direct enable/disable controls. Status writes read the current detail, preserve its public configuration, detect a changed state and use the existing expected revision. Required tools cannot be disabled; conflicts and uncertain outcomes are visible. Backend module routes, models and RBAC are unchanged. `/modules` is a compatible alias showing the settings tools section; `/modules/:id` still opens the tool detail. Reader roles cannot see administration controls.

**我的工具** is an accessible disclosure button, not a catalog link. It reads the current user's enabled and granted tools from `/api/me/modules`, with loading, empty, retry and paginated load-more states. The child route is the existing tool route. Only the open/closed boolean is kept in session storage; tool data and credentials are not persisted. Active children auto-expand, including later pages. The menu has bounded scrolling, works inside the mobile drawer and expands a compact desktop sidebar when opened. Focus/authorization/status changes refresh it; pending requests are cancelled on identity change/unmount. Public demo tools remain separately labeled on home, rather than mixed with personal grants. The old `/tools` URL remains a home-compatible landing for saved return links, with the menu expanded.

Chinese interface wording is consistently 工具, including grants, registration help, diagnostics and errors. Backend identifiers and API contracts remain modules. Older screenshot iterations are archived under [TASK-0043](../TASK-0043/README.md) and [TASK-0044](../TASK-0044/README.md).

## Screenshots

All images are exact viewport captures from intercepted fixture APIs, without real credentials or database data. Desktop and mobile screenshots were visually reviewed for title duplication, hierarchy, menu overflow and control spacing.

| View | 1440×900 | 390×844 |
| --- | --- | --- |
| Home | [desktop](home-1440.png) | [mobile](home-390.png) |
| Users | [desktop](users-1440.png) | [mobile](users-390.png) |
| Global settings | [desktop](settings-1440.png) | [mobile](settings-390.png) |
| Expanded tools | [desktop](tools-expanded-1440.png) | [mobile drawer](tools-expanded-390.png) |
| Tool detail | [desktop](tool-detail-1440.png) | [mobile](tool-detail-390.png) |

## Validation

- Node unit tests: 28 passed. Production Vite build: 74 modules.
- Isolated Windows Chrome fixture covers 1440/390/360 widths, owner/admin/viewer/anonymous roles, single topbar title, inline settings tools, preserved deep links, grants and registration, audit, user protection, account focus/Escape and mobile/compact navigation.
- Personal tools cases include empty/loading/error/retry, 26 authorized tools across two pages with bounded scroll, disabled/ungranted exclusion, child navigation and active-child expansion after reload.
- Inline state cases include conflict, preserving public configuration and required-tool protection. Fixture writes never touch live backend data.
- No backend/schema changes, real database operations, service restart, merge or deployment.

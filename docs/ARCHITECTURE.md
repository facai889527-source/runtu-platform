# Runtu Platform 架构草案

目标：通用模块化 Python 管理平台，不局限于服务器安全。首个业务模块 server_security，未来可扩展 domain_manager、website_monitor、automation、toolbox。

建议技术：FastAPI + Vue 3 + PostgreSQL（中心）+ SQLAlchemy 2 + Alembic；Linux Agent 使用 SQLite 离线队列并通过 HTTPS 主动连接中心。Redis 初期可选。

核心：认证/RBAC、模块注册、配置/密钥、任务调度、事件、通知、审计、统一 Web 界面。各业务模块可独立注册 API、UI、迁移、任务与权限。Agent 可选。

首阶段：最小核心、协作规范、server_security 文件完整性与告警。所有生产部署和自动修复均需用户另行批准。

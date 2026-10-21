# TASK-0023 同步与登录首屏加载验收

## 同步与服务

执行前工作树干净，无未跟踪文件。本地 main 没有独有提交，可从 `84d0621` 安全 fast-forward 到 `4ff4c845d9fe66052f8432ecac18017186398e90`，包含 PR #18 的 squash 合并 `c28e1ccd61c69edec27bd982c83d9937f283e8fb`。原 TASK-0022 分支保留；其原始提交虽因 squash 不在 main 祖先链中，前端及文档内容与远端一致，无覆盖或重置。

按本任务明确授权同步本地 main 后，新建 `codex/TASK-0023-lazy-pages` 开发。本次同步属于正式任务范围，不是状态回传触发的隐式同步。未读取或修改环境秘密、开发 SQLite、管理员引导。现有 FastAPI/Vite 均监听 `127.0.0.1`，8000/5173 登录页和代理健康接口可用，无需重启。额外生产预览只监听本机 4173，验收后按自有监听 PID 核实并停止；原开发服务保持可用。

## 原因与调整

原 App.vue 静态导入所有页面，开发模式浏览器会沿 ESM 依赖图请求 DashboardPage、ModulesPage、SettingsPage 等模块，即使当前只渲染登录页。App.vue 本身是应用入口，仍需加载。304 表示缓存验证后无需重复传输资源，不是页面错误；开发服务器请求数不能直接等同生产请求数或用户可感知速度。

保留轻量导航、JavaScript 和急切加载的登录表单/AuthLayout，将后台外壳、账户菜单及后台页面改为原生 `defineAsyncComponent` + 动态 import。Vue 仅在异步包装组件被渲染时调用加载器，Vite 将动态 import 作为分包边界，参考 [Vue 官方异步组件](https://vuejs.org/guide/components/async.html)。公共加载/错误状态提供等待提示和用户手动重新加载入口，200ms 后才显示等待提示，15 秒加载超时，不自动无限刷新。

无新依赖，无 TypeScript 迁移，无手工 vendor 分包。身份重定向、退出、防伪与权限 API 代码保持不变；可公开的健康及模块资源仍沿用原根组件加载策略。全局后台 CSS 仍在公共样式中，本任务没有声称所有后台资源都从登录页移除，也没有进行网络耗时或真实用户性能基准。

## 实测结果

- Node 单元测试 12 passed；生产构建通过；Python 75 passed、5 PostgreSQL 在线测试 skipped。测试子进程清空开发 DB/认证配置，仅使用临时测试库。
- Chrome 在开发服务和生产预览各运行完整隔离 UI 夹具：1440/390/360 像素下登录布局、已登录跳转、统一账户菜单、角色异常、刷新、退出失败/恢复、退出后夹具 401、侧栏与窄屏焦点约束均通过。新增后台资源加载失败、加载提示、手动重载恢复检查通过。
- 冷启动匿名 `/login`，禁用浏览器缓存，开发模式观察到 18 个脚本请求（含 Vite client、Vue、SFC/CSS 模块），没有 DashboardPage、ModulesPage、SettingsPage、AppLayout 或 UserMenu 脚本请求。
- 相同条件下生产 preview 只观察到 1 个入口 JS 请求 `assets/index-5_JaWCHC.js`，没有上述后台 chunk 请求。该数字不包括 HTML/CSS/API 等非脚本请求，不是页面总请求数。首次进入后台后才加载对应页面及共享依赖。
- 构建 manifest 确认 AppLayout、UserMenu、DashboardPage、ModulesPage、SettingsPage、NotFoundPage 为动态入口。主入口 JS 由上一任务实测 100.59 kB（gzip 38.29）变为 82.84 kB（gzip 33.21）；整个应用总代码没有因此等比例消失。仪表盘 3.86、模块页 7.33、设置页 0.53 kB 为按需 chunk；保留打包器默认共享依赖策略。
- `git diff --check` 通过。未提交生成的 dist、浏览器 profile 或本地记录。

## 复验

仓库根目录执行 `node --test frontend/tests/*.test.js`；构建可使用 `pnpm --dir frontend exec vite build --manifest`，manifest 仅用于本地检查且被忽略。确认 loopback Vite 服务可用后运行 `node frontend/tests/layout-browser-smoke.mjs`。生产预览另开空闲的本机 4173 端口，测试子进程设置 `RUNTU_UI_BASE_URL=http://127.0.0.1:4173` 后运行同一脚本；结束后只停止自己启动的 preview。

脚本拒绝其他来源，拦截所有 API 为明确测试夹具，保存不含凭据的脚本路径证据；拒绝占用的 Chrome 调试端口，使用独立 profile 并关闭自有 headless 浏览器。动态资源请求边界和加载失败恢复需要实际浏览器检查，Node 单元测试不替代它。

无需用户手工改配置或重启开发服务；PR 合并前按需加载改动仅在本开发分支。真实管理员截图中的登录/退出不等于刷新后会话保持和退出后真实受保护 API 验收；TASK-0021 状态仍未标 completed。本任务所有浏览器认证流程均为夹具，不读取用户密码、Cookie、会话或防伪值。

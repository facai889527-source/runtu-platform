// Isolated UI fixtures: intercept every API request; never authenticate a real account.
// Run from repository root against the existing loopback Vite server.
import { spawn } from 'node:child_process'
import { writeFile, mkdir } from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
const origin = process.env.RUNTU_UI_BASE_URL || 'http://127.0.0.1:5173'
assert.ok(['http://127.0.0.1:5173', 'http://127.0.0.1:4173'].includes(origin), 'Only explicit loopback dev/preview origins are supported')
const output = path.resolve('.git/codex-coordination/layout23', new URL(origin).port)
await mkdir(output, { recursive: true })
let occupied = false
try { occupied = (await fetch('http://127.0.0.1:9229/json')).ok } catch { /* Free port. */ }
assert.equal(occupied, false, 'Refusing an occupied browser debug port')
const child = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new',
  '--remote-debugging-port=9229', `--user-data-dir=${output}/chrome-profile`, '--no-first-run',
  '--no-default-browser-check', 'about:blank'], { windowsHide: true, stdio: 'ignore' })
let socket
try {
  let pages
  for (let i = 0; i < 60; i++) {
    try { pages = await (await fetch('http://127.0.0.1:9229/json')).json(); break }
    catch { await new Promise(resolve => setTimeout(resolve, 250)) }
  }
  assert.ok(pages?.length)
  socket = new WebSocket(pages.find(page => page.type === 'page').webSocketDebuggerUrl)
  await new Promise(resolve => socket.addEventListener('open', resolve, { once: true }))
  let loads = 0
  let seq = 0
  const waiting = new Map(), errors = []
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.id) {
      const pending = waiting.get(message.id); waiting.delete(message.id)
      message.error ? pending.reject(new Error('Browser command failed')) : pending.resolve(message.result)
    }
    if (message.method === 'Page.loadEventFired') loads++
    if (message.method === 'Runtime.exceptionThrown') errors.push('Browser runtime exception')
  })
  function send(method, params = {}) {
    return new Promise((resolve, reject) => { const id = ++seq; waiting.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params })) })
  }
  async function evaluate(expression) {
    const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (result.exceptionDetails) throw new Error('Browser evaluation failed')
    return result.result.value
  }
  async function until(expression) {
    for (let i = 0; i < 100; i++) {
      if (await evaluate(expression)) return
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    // Only safe UI state; never dump DOM inputs, network headers or credentials.
    console.log(await evaluate(`({path:location.pathname, heading:document.querySelector('h1')?.textContent, status:document.querySelector('.identity-bar [role=status]')?.textContent, alert:document.querySelector('[role=alert]')?.textContent})`))
    throw new Error('Auth smoke condition timed out')
  }
  async function screenshot(name) {
    // Guard every capture: never record a filled password field.
    assert.equal(await evaluate(`!document.querySelector('input[type=password]')?.value`), true)
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
    await writeFile(path.join(output, name + '.png'), Buffer.from(shot.data, 'base64'))
  }
  let authenticated = false, failLogout = false, failIdentity = false, invalidRole = false
  let failSettings = false, delaySettings = false
  const scriptRequests = new Set()
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.method === 'Network.requestWillBeSent' && message.params.type === 'Script') {
      const url = new URL(message.params.request.url)
      if (url.origin === origin) scriptRequests.add(url.pathname)
    }
  })
  const user = { id: 'layout-fixture-id', username: 'layout-fixture', is_admin: true }
  let module = { id: 'demo', name: '演示模块', version: '1.0.0', description: '仅用于布局验证的模块夹具。', category: 'tools', status: 'enabled', capabilities: ['inspect'], required: false, revision: 0, public_config: { show_in_navigation: true, refresh_interval_seconds: null } }
  let saveStatus = 200, viewer = false
  let apiRequests = 0, sessionWrites = 0
  socket.addEventListener('message', async event => {
    const message = JSON.parse(event.data)
    if (message.method !== 'Fetch.requestPaused') return
    const { requestId, request } = message.params
    try {
      const pathname = new URL(request.url).pathname
      if (!pathname.startsWith('/api/')) {
        if (failSettings) await send('Fetch.failRequest', { requestId, errorReason: 'ConnectionFailed' })
        else {
          if (delaySettings) await new Promise(resolve => setTimeout(resolve, 600))
          await send('Fetch.continueRequest', { requestId })
        }
        return
      }
      apiRequests++
      let code = 200, body
      if (pathname === '/api/health') body = { status: 'ok', platform: 'Runtu Platform', database: 'ready' }
      else if (pathname === '/api/modules') body = [module]
      else if (pathname === '/api/modules/demo') body = module
      else if (pathname === '/api/admin/modules/demo' && request.method === 'PUT') {
        code = saveStatus
        if (code === 200) {
          const value = JSON.parse(request.postData)
          assert.equal(value.expected_revision, module.revision)
          module = { ...module, status: value.enabled ? 'enabled' : 'disabled', public_config: value.public_config, revision: module.revision + 1 }
        }
        body = module
      }
      else if (pathname === '/api/auth/me') {
        code = failIdentity ? 503 : 200
        body = { authenticated, user: authenticated ? user : null }
      } else if (pathname === '/api/admin/me') {
        code = authenticated ? 200 : 401
        body = { ...user, role: invalidRole ? 'unknown' : viewer ? 'viewer' : 'owner', permissions: viewer ? ['platform.read', 'module.read'] : ['platform.read', 'module.read', 'module.manage', 'users.manage', 'audit.read'] }
      } else if (pathname === '/api/auth/csrf') body = { csrf_token: 'a'.repeat(64) } // Public test proof only.
      else if (pathname === '/api/auth/login' || pathname === '/api/auth/logout') {
        assert.equal(request.method, 'POST')
        assert.ok(Object.keys(request.headers).some(key => key.toLowerCase() === 'x-csrf-token'))
        sessionWrites++
        if (pathname.endsWith('logout') && failLogout) code = 503
        else authenticated = pathname.endsWith('login')
        body = { authenticated, user: authenticated ? user : null }
      } else throw new Error('Unexpected API path in isolated fixture')
      await send('Fetch.fulfillRequest', { requestId, responseCode: code, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }], body: Buffer.from(JSON.stringify(body)).toString('base64') })
    } catch {
      errors.push('Fixture request failed')
      await send('Fetch.failRequest', { requestId, errorReason: 'Failed' })
    }
  })
  await send('Runtime.enable'); await send('Page.enable')
  await send('Page.bringToFront')
  await send('Network.enable'); await send('Network.setCacheDisabled', { cacheDisabled: true })
  await send('Fetch.enable', { patterns: [{ urlPattern: origin + '/api/*' }, { urlPattern: origin + '/*SettingsPage*' }] })
  async function loadPage(method, params = {}) {
    const before = loads
    await send(method, params)
    for (let i = 0; i < 100; i++) {
      if (loads > before) return
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    throw new Error('Document load timed out')
  }
  async function visit(pathname) {
    await loadPage('Page.navigate', { url: origin + pathname })
    await until(`document.querySelector('h1') && !document.querySelector('.auth-check')`)
  }
  async function click(selector) { await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`) }
  async function noOverflow() { assert.equal(await evaluate(`document.documentElement.scrollWidth <= innerWidth`), true) }
  for (const [width, height] of [[1440, 900], [390, 844], [360, 800]]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width < 761 })
    authenticated = false
    await visit('/login')
    await until(`document.querySelector('#login-password') && !document.querySelector('#login-password').disabled`)
    assert.equal(await evaluate(`!document.querySelector('.sidebar, .toolbar, .breadcrumb-current, .refresh-button')`), true)
    assert.equal(await evaluate(`document.querySelectorAll('h1').length`), 1)
    await evaluate(`(() => { const el = document.querySelector('#login-username'); el.value = 'layout-fixture'; el.dispatchEvent(new Event('input', { bubbles: true })); window.dispatchEvent(new Event('focus')); })()`)
    await new Promise(resolve => setTimeout(resolve, 100))
    assert.equal(await evaluate(`document.querySelector('#login-username').value`), 'layout-fixture')
    assert.equal(await evaluate(`document.querySelector('.login-submit').getBoundingClientRect().height >= 44`), true)
    await noOverflow(); await screenshot(`login-${width}`)
    if (width === 1440) {
      const scripts = [...scriptRequests].sort()
      assert.ok(scripts.length > 0)
      assert.deepEqual(scripts.filter(url => /(?:DashboardPage|ModulesPage|SettingsPage|AppLayout|UserMenu)[.-]/.test(url)), [], 'Anonymous login must not request workspace chunks')
      await writeFile(path.join(output, 'login-script-requests.json'), JSON.stringify({ origin, scripts, excludedWorkspaceChunks: true }, null, 2))
      console.log(`PASS cold login resource boundary: ${scripts.length} script requests; no workspace/page chunks (${new URL(origin).port})`)
    }
    // Deliberately fake inputs; all APIs above are intercepted, no live account or DB used.
    await evaluate(`(() => { for (const [id, value] of [['login-username','layout-fixture'], ['login-password','fixture-only-not-a-real-password']]) { const el = document.getElementById(id); el.value = value; el.dispatchEvent(new Event('input', { bubbles: true })); } document.querySelector('.login-form').requestSubmit(); })()`)
    await until(`location.pathname === '/' && document.querySelector('.user-menu')`)
    await click('.user-trigger')
    await until(`document.querySelector('.account-role')?.textContent.includes('owner')`)
    assert.equal(await evaluate(`document.querySelectorAll('.sign-out').length === 1 && !document.querySelector('main .sign-out, main .identity-bar, main .access-summary')`), true)
    await noOverflow(); await screenshot(`dashboard-account-${width}`)
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 })
    await until(`document.querySelector('.user-menu') && !document.querySelector('.user-menu').open`)
    assert.equal(await evaluate(`document.activeElement.matches('.user-trigger')`), true)
    await loadPage('Page.reload')
    await until(`document.querySelector('.user-menu') && document.querySelector('.overview-name')`)
    await screenshot(`dashboard-${width}`)
    // An authenticated visit to /login must leave the authentication layout.
    await visit('/login')
    await until(`location.pathname === '/' && document.querySelector('.user-menu')`)
    for (const pathname of ['/modules', '/modules/demo', '/settings']) {
      await visit(pathname)
      await until(`document.querySelector('main')?.textContent.includes(${JSON.stringify(pathname === '/modules' ? '模块目录' : pathname === '/settings' ? '平台设置尚未开放' : '公开配置')})`)
      assert.equal(await evaluate(`!document.querySelector('main .identity-bar, main .access-summary, main .sign-out')`), true)
      await noOverflow(); await screenshot(`${pathname.replaceAll('/', '-')}-${width}`)
    }
    if (width < 761) {
      await click('[aria-label="打开导航"]')
      await until(`document.querySelector('.workspace').inert`)
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 })
      await until(`!document.querySelector('.workspace').inert`)
    } else {
      await click('[aria-label="折叠侧栏"]')
      assert.equal(await evaluate(`document.querySelector('.shell').classList.contains('collapsed')`), true)
      await click('[aria-label="展开侧栏"]')
    }
    if (width === 1440) {
      failLogout = true
      await click('.user-trigger'); await click('.sign-out')
      await until(`document.querySelector('[role=alert]')?.textContent.includes('退出未确认') && document.querySelector('.user-menu')`)
      assert.equal(authenticated, true)
      failLogout = false
      // Re-open only if identity refresh recreated the disclosure.
      if (!await evaluate(`document.querySelector('.user-menu').open`)) await click('.user-trigger')
    } else await click('.user-trigger')
    await click('.sign-out')
    await until(`location.pathname === '/login' && document.querySelector('#login-password')`)
    assert.equal(authenticated, false)
    assert.equal(await evaluate(`fetch('/api/admin/me').then(response => response.status)`), 401)
  }
  failIdentity = true
  await visit('/')
  await until(`document.querySelector('.account-unavailable')`)
  assert.equal(await evaluate(`!document.querySelector('.user-menu')`), true)
  failIdentity = false; authenticated = true; invalidRole = true
  await loadPage('Page.reload')
  await until(`document.querySelector('.user-menu')`)
  await click('.user-trigger')
  await until(`document.querySelector('.account-role')?.textContent.includes('角色暂无法确认')`)
  assert.equal(await evaluate(`document.querySelector('.account-role').textContent.includes('owner')`), false)
  invalidRole = false
  failSettings = true
  await visit('/settings')
  await until(`document.querySelector('.async-view-state[role=alert]')`)
  assert.equal(await evaluate(`document.querySelector('.async-view-state').textContent.includes('页面资源加载失败')`), true)
  failSettings = false; delaySettings = true
  await click('.async-view-state button')
  await until(`document.querySelector('.async-view-state[role=status]')`)
  await until(`document.querySelector('.settings')`)
  delaySettings = false
  await visit('/modules/demo')
  await until(`document.querySelector('.module-editor-form')`)
  await evaluate(`(() => { window.confirm = () => true; const input = document.querySelector('.interval-field input'); input.value = '60'; input.dispatchEvent(new Event('input', { bubbles: true })); document.querySelector('.module-editor input[type=checkbox]').click(); document.querySelector('.module-editor-form').requestSubmit(); })()`)
  await until(`document.querySelector('.save-success') && document.querySelector('.detail-identity').textContent.includes('已禁用')`)
  await screenshot('module-management-saved')
  assert.equal(module.public_config.refresh_interval_seconds, 60)
  await loadPage('Page.reload')
  await until(`document.querySelector('.interval-field input')?.value === '60'`)
  assert.equal(await evaluate(`document.querySelector('.module-editor input[type=checkbox]').checked`), false)
  for (saveStatus of [409, 503]) {
    await evaluate(`document.querySelector('.module-editor-form').requestSubmit()`)
    await until(`document.querySelector('.module-editor [role=alert]')`)
    assert.equal(module.revision, 1)
  }
  saveStatus = 200
  authenticated = false
  await loadPage('Page.reload')
  await until(`document.querySelector('.module-editor a')`)
  assert.equal(await evaluate(`!document.querySelector('.module-editor-form')`), true)
  authenticated = true; viewer = true
  await loadPage('Page.reload')
  await until(`document.querySelector('.module-editor')?.textContent.includes('没有模块管理权限')`)
  assert.equal(await evaluate(`!document.querySelector('.module-editor-form')`), true)
  assert.ok(apiRequests > 0 && sessionWrites >= 6)
  assert.deepEqual(errors, [])
  console.log('PASS isolated UI fixtures: login, roles, logout, responsive navigation, lazy loading, module save/config/reload/409/503 and anonymous management denial. No real admin login verified.')
} finally { socket?.close(); child.kill() }

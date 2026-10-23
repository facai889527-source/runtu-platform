// Isolated UI fixtures: intercept every API request; never authenticate a real account.
// Run from repository root against the existing loopback Vite server.
import { spawn } from 'node:child_process'
import { writeFile, mkdir } from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
const origin = process.env.RUNTU_UI_BASE_URL || 'http://127.0.0.1:5173'
assert.ok(['http://127.0.0.1:5173', 'http://127.0.0.1:4173'].includes(origin), 'Only explicit loopback dev/preview origins are supported')
const output = path.resolve('.git/codex-coordination/task46-after', new URL(origin).port)
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
      if (!pending) return
      clearTimeout(pending.timer)
      message.error ? pending.reject(new Error(message.error.message || 'Browser command failed')) : pending.resolve(message.result)
    }
    if (message.method === 'Page.loadEventFired') loads++
    if (message.method === 'Runtime.exceptionThrown') errors.push('Browser runtime exception')
    if (message.method === 'Page.javascriptDialogOpening') send('Page.handleJavaScriptDialog', { accept: true }).catch(() => {})
  })
  function send(method, params = {}) {
    return new Promise((resolve, reject) => { const id = ++seq; const timer = setTimeout(() => { waiting.delete(id); reject(new Error('Browser command timed out: ' + method)) }, 15000); waiting.set(id, { resolve, reject, timer }); socket.send(JSON.stringify({ id, method, params })) })
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
    console.log(await evaluate(`({path:location.pathname, heading:document.querySelector('h1')?.textContent, status:document.querySelector('.my-modules')?.textContent, alert:document.querySelector('[role=alert]')?.textContent})`))
    throw new Error('Auth smoke condition timed out')
  }
  async function screenshot(name) {
    await until(`!document.querySelector('.auth-toast-enter-active, .auth-toast-leave-active')`)
    // Guard every capture: never record a filled password field.
    assert.equal(await evaluate(`!document.querySelector('input[type=password]')?.value`), true)
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
    await writeFile(path.join(output, name + '.png'), Buffer.from(shot.data, 'base64'))
  }
  let authenticated = false, failLogout = false, failIdentity = false, invalidRole = false
  let loginStatus = 200, delayLogin = false
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
  let module = { id: 'demo', name: '演示工具', version: '1.0.0', description: '仅用于布局验证的工具夹具。', category: 'tools', status: 'enabled', capabilities: ['inspect'], required: false, revision: 0, public_config: { show_in_navigation: true, refresh_interval_seconds: null } }
  let saveStatus = 200, viewer = false, admin = false
  let usersStatus = 200, usersWriteStatus = 200, userRequests = 0
  const grantSets = new Map()
  let activityHistory = null, activityStatus = 200
  let ownStatus = 200, ownDelay = false, ownExtraRows = []
  let grantStatus = 200, emptyGrantCandidates = false
  const grantCandidates = [{ module_id:'alpha',name:'受保护业务示例',enabled:true },{ module_id:'beta',name:'停用业务示例',enabled:false }]
  let managedUsers = [{ id: 'layout-fixture-id', username: 'layout-fixture', role: 'owner', active: true, created_at: '2026-10-21T08:00:00Z' }, ...Array.from({ length: 21 }, (_, index) => ({ id: `user-fixture-${index}`, username: `user-${String(index).padStart(3,'0')}`, role: 'viewer', active: true, created_at: '2026-10-21T08:00:00Z' }))]
  let auditEntries = [], auditStatus = 200, auditRequests = 0, delayAudit = false
  let apiRequests = 0, sessionWrites = 0
  let registrationPolicy = { enabled:false, approval_required:true, revision:0 }, registrationStatus = 200
  let applications = []
  let policyReads = 0, failPolicyNetwork = false, delayPolicy = false
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
      else if (pathname === '/api/auth/registration-policy') {
        policyReads++
        if (delayPolicy) await new Promise(resolve=>setTimeout(resolve,500))
        if (failPolicyNetwork) { await send('Fetch.failRequest',{requestId,errorReason:'ConnectionFailed'}); return }
        code=registrationStatus; body={enabled:registrationPolicy.enabled,approval_required:registrationPolicy.approval_required}
      }
      else if (pathname === '/api/auth/register') {
        assert.ok(Object.keys(request.headers).some(k=>k.toLowerCase()==='x-csrf-token'))
        const value=JSON.parse(request.postData); assert.equal(value.role,undefined)
        assert.ok(value.password.length>=14)
        code=registrationPolicy.enabled?202:403; body={state:'submitted'}
        if(code===202) applications=[{id:'registration-fixture',username:value.username,state:'pending'}]
      }
      else if (pathname === '/api/admin/registration-policy') {
        code=!authenticated?401:viewer||admin?403:registrationStatus
        if(code===200&&request.method==='PUT') {
          const value=JSON.parse(request.postData); assert.equal(value.expected_revision,registrationPolicy.revision)
          assert.ok(Object.keys(request.headers).some(k=>k.toLowerCase()==='x-csrf-token'))
          registrationPolicy={enabled:value.enabled,approval_required:value.approval_required,revision:registrationPolicy.revision+1}
        }
        body=registrationPolicy
      }
      else if (pathname === '/api/admin/registrations' || pathname.startsWith('/api/admin/registrations/')) {
        code=!authenticated?401:viewer||admin?403:registrationStatus
        if(request.method==='POST') { assert.ok(Object.keys(request.headers).some(k=>k.toLowerCase()==='x-csrf-token')); applications=[]; body={state:'approved'} }
        else body={items:applications,next_after_username:null}
      }
      else if (pathname === '/api/me/modules') {
        if(ownDelay) await new Promise(resolve=>setTimeout(resolve,600))
        code = authenticated ? ownStatus : 401
        const after = new URL(request.url).searchParams.get('after_module')
        const rows = [...grantCandidates.filter(row => row.enabled && grantSets.get(user.id)?.has(row.module_id)).map(row => ({...row,granted:true})), ...ownExtraRows].sort((a,b)=>a.module_id.localeCompare(b.module_id)).filter(row=>after==null||row.module_id>after)
        body = {items:rows.slice(0,20),next_after_module:rows.length>20?rows[19].module_id:null}
      }
      else if (/^\/api\/admin\/users\/[^/]+\/modules(?:\/[^/]+)?$/.test(pathname)) {
        code = !authenticated ? 401 : viewer || admin ? 403 : grantStatus
        const parts=pathname.split('/'), id=parts[4], moduleId=parts[6]
        const assigned=grantSets.get(id)||new Set()
        if(code===200&&request.method==='PUT') {
          const value=JSON.parse(request.postData)
          assert.ok(Object.keys(request.headers).some(key=>key.toLowerCase()==='x-csrf-token'))
          value.granted ? assigned.add(moduleId) : assigned.delete(moduleId)
          grantSets.set(id,assigned)
          body={...grantCandidates.find(row=>row.module_id===moduleId),granted:value.granted}
        } else body={items:emptyGrantCandidates?[]:grantCandidates.map(row=>({...row,granted:assigned.has(row.module_id)})),next_after_module:null}
      }
      else if (pathname === '/api/admin/users' || pathname.startsWith('/api/admin/users/')) {
        userRequests++
        code = !authenticated ? 401 : viewer || admin ? 403 : request.method === 'GET' ? usersStatus : usersWriteStatus
        if (code === 200 && request.method === 'GET') {
          const after = new URL(request.url).searchParams.get('after_username')
          const rows = managedUsers.filter(item => after == null || item.username > after).sort((a,b) => a.username < b.username ? -1 : 1)
          body = { items: rows.slice(0,20), next_after_username: rows.length > 20 ? rows[19].username : null }
        } else if (code === 200 && request.method === 'POST') {
          assert.ok(Object.keys(request.headers).some(key => key.toLowerCase() === 'x-csrf-token'))
          const value = JSON.parse(request.postData)
          assert.ok(value.password.length >= 14)
          body = { id: 'new-fixture-id', username: value.username, role: value.role, active: true, created_at: '2026-10-21T08:00:00Z' }
          managedUsers.push(body); code = 201
        } else if (code === 200 && request.method === 'PATCH') {
          const id = pathname.split('/').at(-1), value = JSON.parse(request.postData)
          assert.notEqual(id, user.id)
          const index = managedUsers.findIndex(item => item.id === id)
          assert.equal(managedUsers[index].role, value.expected_role)
          assert.equal(managedUsers[index].active, value.expected_active)
          managedUsers[index] = { ...managedUsers[index], role: value.role, active: value.active }
          body = managedUsers[index]
        } else body = { detail: 'fixture-user-error' }
      }
      else if (pathname === '/api/modules') body = [module, { ...module, id:'alpha',name:'受保护业务示例',access_mode:'assigned' }]
      else if (pathname === '/api/modules/alpha') body = {...module,id:'alpha',name:'受保护业务示例',access_mode:'assigned'}
      else if (pathname === '/api/admin/modules/alpha/changes') body = {items:[],next_before_revision:null}
      else if (pathname === '/api/modules/demo') body = module
      else if (pathname === '/api/admin/modules/demo/changes') {
        auditRequests++
        if (delayAudit) await new Promise(resolve => setTimeout(resolve, 600))
        code = !authenticated ? 401 : viewer ? 403 : auditStatus
        const before = new URL(request.url).searchParams.get('before_revision')
        const rows = auditEntries.filter(row => before == null || row.revision < Number(before))
        body = code === 200 ? { items: rows.slice(0, 10), next_before_revision: rows.length > 10 ? rows[9].revision : null } : { detail: 'fixture-denied' }
      }
      else if (pathname === '/api/admin/modules/demo' && request.method === 'PUT') {
        code = saveStatus
        if (code === 200) {
          const value = JSON.parse(request.postData)
          assert.equal(value.expected_revision, module.revision)
          module = { ...module, status: value.enabled ? 'enabled' : 'disabled', public_config: value.public_config, revision: module.revision + 1 }
          auditEntries.unshift({ module_id: 'demo', actor_id: 'fixture-actor', action: 'updated', revision: module.revision, created_at: '2026-10-21T08:00:00Z' })
        }
        body = module
      }
      else if (pathname === '/api/auth/activity') { code = authenticated ? activityStatus : 401; body = { previous_login: activityHistory } }
      else if (pathname === '/api/auth/me') {
        code = failIdentity ? 503 : 200
        body = { authenticated, user: authenticated ? user : null }
      } else if (pathname === '/api/admin/me') {
        code = authenticated ? 200 : 401
        body = { ...user, role: invalidRole ? 'unknown' : viewer ? 'viewer' : admin ? 'admin' : 'owner', permissions: viewer ? ['platform.read', 'module.read'] : admin ? ['platform.read','module.read','module.manage','audit.read'] : ['platform.read', 'module.read', 'module.manage', 'users.manage', 'audit.read'] }
      } else if (pathname === '/api/auth/csrf') body = { csrf_token: 'a'.repeat(64) } // Public test proof only.
      else if (pathname === '/api/auth/login' || pathname === '/api/auth/logout') {
        assert.equal(request.method, 'POST')
        assert.ok(Object.keys(request.headers).some(key => key.toLowerCase() === 'x-csrf-token'))
        sessionWrites++
        if (pathname.endsWith('login') && delayLogin) await new Promise(resolve=>setTimeout(resolve,600))
        if (pathname.endsWith('login') && loginStatus !== 200) code = loginStatus
        else if (pathname.endsWith('logout') && failLogout) code = 503
        else authenticated = pathname.endsWith('login')
        body = { authenticated, user: authenticated ? user : null }
      } else throw new Error('Unexpected API path in isolated fixture')
      await send('Fetch.fulfillRequest', { requestId, responseCode: code, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }], body: Buffer.from(JSON.stringify(body)).toString('base64') })
    } catch (failure) {
      // Explicit abort/unmount tests can remove an interception before its delayed reply.
      if (/Invalid InterceptionId|Invalid interceptionId|Invalid RequestId|Invalid requestId/i.test(failure.message)) return
      errors.push('Fixture request failed')
      try { await send('Fetch.failRequest', { requestId, errorReason: 'Failed' }) } catch { /* interception already removed */ }
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
  if (process.env.RUNTU_HOME_ONLY === '1') {
    for (const [width,height] of [[1440,900],[390,844],[360,800]]) {
      await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<761})
      authenticated=true;activityStatus=200;user.username='layout-fixture'
      for (const role of ['owner','admin','viewer']) {
        viewer=role==='viewer';admin=role==='admin';activityHistory=null;ownExtraRows=[];grantSets.clear()
        await visit('/')
        await until(`document.querySelector('.account-facts')?.textContent.includes(${JSON.stringify(role==='owner'?'所有者':role==='admin'?'管理员':'只读成员')}) && document.querySelector('.authorized-total strong')?.textContent==='0'`)
        assert.equal(await evaluate(`Boolean(document.querySelector('.system-status'))`),role==='owner')
        assert.equal(await evaluate(`!document.querySelector('main h1') && document.querySelector('.toolbar h1').textContent==='首页'`),true)
        await noOverflow();await screenshot(`home-${role}-empty-${width}`)
        activityHistory={at:'2026-10-22T08:45:00+00:00',ip:'198.51.100.24'}
        ownExtraRows=Array.from({length:26},(_,i)=>({module_id:'tool_'+String(i).padStart(2,'0'),name:'授权夹具工具 '+i,enabled:true,granted:true}))
        await loadPage('Page.reload')
        await until(`document.querySelector('.authorized-total strong')?.textContent==='26' && document.querySelector('.login-activity')?.textContent.includes('198.51.100.24')`)
        await noOverflow();await screenshot(`home-${role}-history-many-${width}`)
      }
      user.username='member-'+ 'x'.repeat(50)
      await loadPage('Page.reload')
      await until(`document.querySelector('#welcome-title')?.textContent.includes('member-')`)
      await noOverflow();await screenshot(`home-long-name-${width}`)
      activityHistory={at:'2026-10-22T08:45:00Z',ip:null}
      await loadPage('Page.reload')
      await until(`document.querySelector('.login-activity')?.textContent.includes('未记录')`)
      assert.equal(await evaluate(`document.querySelector('.login-activity').textContent.includes('暂无记录')`),false)
      authenticated=false
      await visit('/')
      await until(`location.pathname==='/login' && document.querySelector('#login-password')`)
      assert.equal(await evaluate(`!document.querySelector('.home-welcome, .login-activity')`),true)
    }
    assert.deepEqual(errors,[])
    console.log('PASS personalized home: owner/admin/viewer/anonymous, no history/UTC history/no IP, 0/26 tools, long username, 1440/390/360; no live account used.')
  } else {
  for (const [width, height] of [[1440, 900], [390, 844], [360, 800]]) {
    auditEntries = []
    grantSets.clear()
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width < 761 })
    authenticated = false
    for (const target of ['/', '/modules', '/modules/demo', '/settings', '/users']) {
      await visit(target)
      await until(`location.pathname === '/login' && document.querySelector('#login-password')`)
      assert.equal(await evaluate(`!document.querySelector('.sidebar, .user-menu, .module-list, .users-page, .registration-policy')`),true)
      assert.equal(await evaluate(`new URLSearchParams(location.search).get('returnTo')`),target)
      await loadPage('Page.reload')
      await until(`document.querySelector('#login-password')`)
    }
    await visit('/login')
    await until(`document.querySelector('#login-password') && !document.querySelector('#login-password').disabled`)
    assert.equal(await evaluate(`!document.querySelector('.sidebar, .toolbar, .breadcrumb-current, .refresh-button')`), true)
    assert.equal(await evaluate(`document.querySelectorAll('h1').length`), 1)
    assert.equal(await evaluate(`document.querySelector('.login-help').textContent.replace(/\s+/g,' ').trim()`),'没有账户？ 申请注册账号')
    assert.equal(await evaluate(`document.querySelectorAll('.login-help a').length`),1)
    await evaluate(`(() => { const el = document.querySelector('#login-username'); el.value = 'layout-fixture'; el.dispatchEvent(new Event('input', { bubbles: true })); window.dispatchEvent(new Event('focus')); })()`)
    await new Promise(resolve => setTimeout(resolve, 100))
    assert.equal(await evaluate(`document.querySelector('#login-username').value`), 'layout-fixture')
    assert.equal(await evaluate(`document.querySelector('.login-submit').getBoundingClientRect().height >= 44`), true)
    await noOverflow(); await screenshot(`login-${width}`)
    if (width === 1440) {
      const scripts = [...scriptRequests].sort()
      assert.ok(scripts.length > 0)
      assert.deepEqual(scripts.filter(url => /(?:DashboardPage|ModulesPage|SettingsPage|UsersPage|AppLayout|UserMenu)[.-]/.test(url)), [], 'Anonymous login must not request workspace chunks')
      await writeFile(path.join(output, 'login-script-requests.json'), JSON.stringify({ origin, scripts, excludedWorkspaceChunks: true }, null, 2))
      console.log(`PASS cold login resource boundary: ${scripts.length} script requests; no workspace/page chunks (${new URL(origin).port})`)
    }
    await evaluate(`document.querySelector('#login-username').focus()`)
    await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9})
    await until(`document.activeElement.id === 'login-password'`)
    const beforePolicyReads = policyReads
    delayPolicy=true
    await evaluate(`document.querySelector('.login-help a').click();document.querySelector('.login-help a').click()`)
    await until(`document.querySelector('.signup-pending')?.textContent.includes('正在确认')`)
    await until(`document.querySelector('.auth-toast span')?.textContent === '管理员未开启注册'`)
    assert.equal(await evaluate(`location.pathname`),'/login')
    assert.equal(policyReads,beforePolicyReads+1)
    await click('.login-help a')
    assert.equal(policyReads,beforePolicyReads+1)
    assert.equal(await evaluate(`Boolean(document.querySelector('.register-panel, .registration-closed'))`),false)
    assert.equal(await evaluate(`document.querySelector('#login-title').textContent`),'欢迎回来')
    assert.equal(await evaluate(`document.querySelector('.login-context p').textContent`),'登录润土平台，开启高效工作')
    assert.equal(await evaluate(`document.querySelector('.auth-toast-region').getAttribute('aria-live')`),'polite')
    assert.equal(await evaluate(`Boolean(document.querySelector('.signup-notice'))`),false)
    await noOverflow(); await screenshot(`signup-closed-${width}`)
    await click('.auth-toast button')
    await until(`!document.querySelector('.auth-toast')`)
    await click('.login-help a')
    await until(`document.querySelector('.auth-toast span')?.textContent === '管理员未开启注册'`)
    assert.equal(policyReads,beforePolicyReads+1)
    await until(`!document.querySelector('.auth-toast')`)
    assert.equal(await evaluate(`location.pathname`),'/login')
    delayPolicy=false
    // A direct URL remains public, but closed policy has no form or retry control.
    await visit('/register')
    await until(`document.querySelector('.registration-closed')?.textContent.includes('暂未开放注册')`)
    assert.equal(await evaluate(`Boolean(document.querySelector('.register-panel form, .register-panel input, .register-panel button'))`),false)
    await screenshot(`registration-closed-${width}`)
    for (const failure of [404,503,'network']) {
      registrationStatus=failure === 'network'?200:failure;failPolicyNetwork=failure === 'network'
      await visit('/login')
      await click('.login-help a')
      await until(`document.querySelector('.auth-toast span')?.textContent === '注册服务暂不可用，请稍后再试'`)
      assert.equal(await evaluate(`location.pathname`),'/login')
      assert.equal(await evaluate(`document.querySelector('.auth-toast span').textContent.includes('暂未开放')`),false)
      if(failure===503) { await screenshot(`signup-unavailable-${width}`); await until(`!document.querySelector('.auth-toast')`) }
    }
    registrationStatus=200;failPolicyNetwork=false
    registrationPolicy.enabled=true
    await visit('/login')
    await click('.login-help a')
    await until(`location.pathname === '/register' && document.querySelector('.register-panel form')`)
    // Unmount an in-flight check: its late response must not navigate away.
    await click('.login-link')
    delayPolicy=true
    await click('.login-help a')
    await until(`document.querySelector('.signup-pending')?.textContent.includes('正在确认')`)
    await evaluate(`history.pushState(null,'','/register');window.dispatchEvent(new PopStateEvent('popstate'))`)
    await until(`location.pathname === '/register' && document.querySelector('.register-panel form')`)
    delayPolicy=false;registrationPolicy.enabled=false
    await visit('/login')
    await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]})
    assert.equal(await evaluate(`getComputedStyle(document.querySelector('#login-username')).transitionDuration`),'0s')
    await click('.login-help a')
    await until(`document.querySelector('.auth-toast')`)
    assert.equal(await evaluate(`getComputedStyle(document.querySelector('.auth-toast')).transitionDuration`),'0s')
    await click('.auth-toast button')
    await until(`!document.querySelector('.auth-toast')`)
    await send('Emulation.setEmulatedMedia',{features:[]})
    delayLogin=true
    for (loginStatus of [401,403,503]) {
      await evaluate(`(() => { for (const [id,value] of [['login-username','layout-fixture'],['login-password','fixture-only-not-a-real-password']]) { const el=document.getElementById(id);el.value=value;el.dispatchEvent(new Event('input',{bubbles:true})); } document.querySelector('.login-form').requestSubmit() })()`)
      await until(`document.querySelector('.login-submit').disabled && document.querySelector('#login-password').value === ''`)
      await until(`document.querySelector('.auth-error') && !document.querySelector('.login-submit').disabled`)
      assert.equal(authenticated,false)
      assert.equal(await evaluate(`!document.querySelector('.sidebar, .user-menu')`),true)
      await noOverflow()
    }
    await screenshot(`login-unavailable-${width}`)
    loginStatus=200;delayLogin=false
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
    await until(`document.querySelector('.user-menu') && document.querySelector('.my-modules') && document.querySelector('.overview-name')`)
    assert.equal(await evaluate(`document.querySelector('h1').textContent === '首页' && document.querySelectorAll('.sidebar nav > a').length === 3 && !document.querySelector('.system-status').open`), true)
    assert.deepEqual(await evaluate(`Array.from(document.querySelectorAll('.sidebar nav > a, .tools-toggle')).map(el=>el.textContent.trim())`), ['首页','我的工具','用户管理','全局设置'])
    assert.equal(await evaluate(`!document.querySelector('.platform-context, .nav-caption') && document.querySelector('.toolbar-title').textContent.trim() === '首页' && !document.querySelector('main h1, .page-intro') && document.querySelector('.brand-sub').textContent === '多功能工具平台'`), true)
    await until(`document.querySelector('.login-activity')?.textContent.includes('暂无记录') && document.querySelector('.authorized-total strong')?.textContent==='0'`)
    assert.equal(await evaluate(`document.querySelector('#welcome-title').textContent`),'layout-fixture，您好！')
    await screenshot(`dashboard-${width}`)
    activityHistory={at:'2026-10-22T08:45:00+00:00',ip:'198.51.100.24'}
    await loadPage('Page.reload')
    await until(`document.querySelector('.login-activity')?.textContent.includes('198.51.100.24')`)
    await noOverflow(); await screenshot(`home-history-${width}`)
    activityStatus=503
    await loadPage('Page.reload')
    await until(`document.querySelector('.login-activity')?.textContent.includes('登录记录暂不可用')`)
    assert.equal(await evaluate(`document.querySelector('.login-activity').textContent.includes('暂无记录')`),false)
    activityStatus=200;activityHistory=null
    await click('.activity-error button')
    await until(`document.querySelector('.login-activity')?.textContent.includes('暂无记录')`)

    if(width===1440){
      await evaluate(`document.querySelector('.tools-toggle').click()`)
      await until(`document.querySelector('.tools-empty')`)
      ownStatus=503
      await evaluate(`window.dispatchEvent(new Event('runtu-tools-changed'))`)
      await until(`document.querySelector('.tools-children [role=alert]')`)
      assert.equal(await evaluate(`document.querySelectorAll('.tools-children a').length`),0)
      ownStatus=200;ownDelay=true
      await click('.tools-children [role=alert] button')
      await until(`document.querySelector('.tools-children [role=status]')`)
      await until(`document.querySelector('.tools-empty')`)
      ownDelay=false
    }

    await visit('/tools')
    await until(`document.querySelector('h1')?.textContent === '我的工具' && document.querySelector('.my-modules')`)
    assert.equal(await evaluate(`!document.querySelector('.sidebar a[href="/tools"]')`), true)
    // An authenticated visit to /login must leave the authentication layout.
    await visit('/login')
    await until(`location.pathname === '/' && document.querySelector('.user-menu')`)
    for (const pathname of ['/modules', '/modules/demo', '/settings']) {
      await visit(pathname)
      await until(`document.querySelector('main')?.textContent.includes(${JSON.stringify(pathname === '/modules' ? '工具管理' : pathname === '/settings' ? '注册策略' : '公开配置')})`)
      if(pathname !== '/modules/demo') assert.equal(await evaluate(`document.querySelector('.sidebar [aria-current=page]')?.textContent.trim()`),'全局设置')
      if (pathname === '/settings' || pathname === '/modules') {
        assert.equal(await evaluate(`document.querySelector('.toolbar h1').textContent`),'全局设置')
        assert.equal(await evaluate(`Boolean(document.querySelector('.directory-panel .module-list')) && !document.querySelector('.settings-module-link')`),true)
      }
      if (pathname === '/modules/demo') {
        await until(`document.querySelector('.module-audit')?.textContent.includes('此工具暂无操作记录')`)
        auditEntries = Array.from({ length: 12 }, (_, index) => ({ module_id: 'demo', actor_id: 'fixture-actor-identifier-123456789', action: 'updated', revision: 12-index, created_at: '2026-10-21T08:00:00Z' }))
        delayAudit = true
        await click('.module-audit .section-heading button')
        await until(`document.querySelector('.module-audit [role=status]')?.textContent.includes('正在加载操作记录')`)
        await until(`document.querySelectorAll('.audit-list li').length === 10`)
        delayAudit = false
        await click('.audit-pagination button:last-child')
        await until(`document.querySelectorAll('.audit-list li').length === 2`)
        await click('.audit-pagination button:first-child')
        await until(`document.querySelector('.audit-list li')?.textContent.includes('版本 12')`)
        await noOverflow(); await screenshot(`module-audit-${width}`)
      }
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
    await visit('/users')
    await until(`document.querySelectorAll('.managed-user').length === 20`)
    assert.equal(await evaluate(`document.querySelector('.managed-user fieldset').disabled`), true)
    emptyGrantCandidates=true
    await click('.managed-user:first-child .user-module-access > button')
    await until(`document.querySelector('.grant-content')?.textContent.includes('当前没有可授权的受保护业务工具')`)
    emptyGrantCandidates=false
    await click('.grant-content > button')
    await until(`document.querySelector('.grant-items input')`)
    await evaluate(`window.confirm=()=>true; document.querySelector('.grant-items input').click()`)
    await until(`document.querySelector('.grant-content [role=status]')?.textContent.includes('工具授权已保存')`)
    assert.equal(grantSets.get(user.id)?.has('alpha'),true)
    await evaluate(`document.querySelector('.grant-content').scrollIntoView({block:'center'})`)
    await noOverflow(); await screenshot(`grant-editor-${width}`)
    await visit('/')
    await until(`document.querySelector('.my-modules a')?.textContent === '受保护业务示例'`)
    assert.equal(await evaluate(`document.querySelector('.my-modules').textContent.includes('停用业务示例')`),false)
    await evaluate(`document.querySelector('.my-modules').scrollIntoView({block:'center'})`)
    await noOverflow(); await screenshot(`my-modules-${width}`)
    await until(`document.querySelector('.tools-children a[href="/modules/alpha"]')`)
    {
      ownExtraRows=Array.from({length:25},(_,i)=>({module_id:'tool_'+String(i).padStart(2,'0'),name:'授权夹具工具 '+i,enabled:true,granted:true}))
      await evaluate(`window.dispatchEvent(new Event('runtu-tools-changed'))`)
      await until(`document.querySelectorAll('.tools-children li').length===20`)
      await evaluate(`document.querySelector('.tools-more').click()`)
      await until(`document.querySelectorAll('.tools-children li').length===26`)
      assert.equal(await evaluate(`document.querySelector('.tools-children').scrollHeight>document.querySelector('.tools-children').clientHeight`),true)
      await until(`document.querySelector('.authorized-total strong')?.textContent==='26'`)
      await evaluate(`window.scrollTo(0,0); new Promise(resolve=>requestAnimationFrame(resolve))`)
      await noOverflow(); await screenshot(`home-many-tools-${width}`)
      ownExtraRows=[]
      await evaluate(`window.dispatchEvent(new Event('runtu-tools-changed'))`)
      await until(`document.querySelectorAll('.tools-children li').length===1`)
    }

    assert.equal(await evaluate(`!document.querySelector('.tools-children a[href="/modules/beta"]')`),true)
    if (!await evaluate(`document.querySelector('.tools-toggle').getAttribute('aria-expanded') === 'true'`)) await evaluate(`document.querySelector('.tools-toggle').click()`)
    if(width<761) await click('[aria-label="打开导航"]')
    await noOverflow(); await screenshot(`tools-expanded-${width}`)
    await click('.tools-children a[href="/modules/alpha"]')
    await until(`location.pathname === '/modules/alpha' && document.querySelector('.detail-identity')`)
    assert.equal(await evaluate(`document.querySelector('.tools-toggle').getAttribute('aria-expanded')`),'true')
    assert.equal(await evaluate(`document.querySelector('.toolbar h1').textContent`),'工具详情')
    await noOverflow(); await screenshot(`tool-detail-${width}`)
    await loadPage('Page.reload')
    await until(`document.querySelector('.tools-children a[aria-current=page]')`)
    assert.equal(await evaluate(`document.querySelector('.tools-toggle').getAttribute('aria-expanded')`),'true')

    await visit('/users')
    await until(`document.querySelectorAll('.managed-user').length === 20`)
    await noOverflow(); await screenshot(`users-${width}`)
    await click('.user-pagination button:last-child')
    await until(`document.querySelectorAll('.managed-user').length === 2`)
    await click('.user-pagination button:first-child')
    await until(`document.querySelectorAll('.managed-user').length === 20`)
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
  await until(`document.querySelector('.auth-layout [role=alert]')`)
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
  await until(`document.querySelector('.registration-policy')`)
  delaySettings = false
  auditEntries = []
  await visit('/modules/demo')
  await until(`document.querySelector('.module-editor-form')`)
  await evaluate(`(() => { window.confirm = () => true; const input = document.querySelector('.interval-field input'); input.value = '60'; input.dispatchEvent(new Event('input', { bubbles: true })); document.querySelector('.module-editor input[type=checkbox]').click(); document.querySelector('.module-editor-form').requestSubmit(); })()`)
  await until(`document.querySelector('.save-success') && document.querySelector('.detail-identity').textContent.includes('已禁用')`)
  await screenshot('module-management-saved')
  await until(`document.querySelector('.audit-list li')?.textContent.includes('版本 1')`)
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
  for (auditStatus of [503, 403]) {
    await click('.module-audit .section-heading button')
    await until(`document.querySelector('.module-audit [role=alert]')`)
    assert.equal(await evaluate(`document.querySelectorAll('.audit-list li').length`), 0)
  }
  auditStatus = 200
  await click('.module-audit .section-heading button')
  await until(`document.querySelector('.audit-list li')`)
  const allowedAuditRequests = auditRequests
  authenticated = false
  await loadPage('Page.reload')
  await until(`location.pathname === '/login' && document.querySelector('#login-password')`)
  assert.equal(await evaluate(`!document.querySelector('.sidebar, .module-editor, .module-audit')`), true)
  assert.equal(auditRequests, allowedAuditRequests)
  authenticated = true; viewer = true
  await loadPage('Page.reload')
  await until(`document.querySelector('.detail-identity')`)
  assert.equal(await evaluate(`!document.querySelector('.module-editor-form')`), true)
  assert.equal(await evaluate(`!document.querySelector('.module-editor, .module-audit')`),true)
  assert.equal(auditRequests, allowedAuditRequests)
  assert.equal(await evaluate(`document.querySelectorAll('.sidebar nav > a').length === 1 && !document.querySelector('.system-status')`), true)
  const previousUserRequests = userRequests
  await visit('/modules')
  await until(`document.querySelector('.settings')?.textContent.includes('没有全局设置权限')`)
  assert.equal(await evaluate(`!document.querySelector('.module-list')`),true)
  await visit('/users')
  await until(`document.querySelector('main')?.textContent.includes('没有用户管理权限')`)
  assert.equal(userRequests, previousUserRequests)
  viewer = false; admin = true
  await loadPage('Page.reload')
  await until(`document.querySelector('main')?.textContent.includes('没有用户管理权限')`)
  assert.equal(userRequests, previousUserRequests)
  assert.equal(await evaluate(`document.querySelectorAll('.sidebar nav > a').length === 2 && !document.querySelector('.sidebar a[href="/modules"]') && Boolean(document.querySelector('.sidebar a[href="/settings"]'))`), true)
  await visit('/settings')
  await until(`document.querySelector('.directory-panel .module-list')`)
  assert.equal(await evaluate(`!document.querySelector('.registration-policy, .approvals')`),true)
  await visit('/modules')
  await until(`document.querySelector('.directory-panel .module-list')`)
  assert.equal(userRequests,previousUserRequests)
  admin = false; authenticated = false
  await loadPage('Page.reload')
  await until(`location.pathname === '/login' && document.querySelector('#login-password')`)
  assert.equal(userRequests, previousUserRequests)
  authenticated = true
  await visit('/users')
  await until(`document.querySelector('.user-create-form') && document.querySelectorAll('.managed-user').length === 20`)
  await click('.create-disclosure > summary')
  assert.equal(await evaluate(`document.querySelector('.create-disclosure').open`), true)
  await evaluate(`(() => { window.confirm=()=>true; const name=document.querySelector('.user-create-form input:not([type=password])'); name.value='fixture-new'; name.dispatchEvent(new Event('input',{bubbles:true})); document.querySelector('.user-create-form input[type=password]').value=crypto.randomUUID(); document.querySelector('.user-create-form').requestSubmit(); })()`)
  await until(`document.querySelector('.user-create [role=status]') && document.querySelector('.managed-user h3')?.textContent === 'fixture-new'`)
  assert.equal(await evaluate(`document.querySelector('.user-create-form input[type=password]').value`),'')
  await evaluate(`(() => { const row=document.querySelector('.managed-user'); row.querySelector('.user-active input').click(); row.querySelector('form').requestSubmit(); })()`)
  await until(`document.querySelector('.managed-user-heading')?.textContent.includes('已禁用')`)
  await screenshot('users-created-disabled')
  usersWriteStatus = 409
  await evaluate(`(() => { const name=document.querySelector('.user-create-form input:not([type=password])'); name.value='fixture-new'; name.dispatchEvent(new Event('input',{bubbles:true})); document.querySelector('.user-create-form input[type=password]').value=crypto.randomUUID(); document.querySelector('.user-create-form').requestSubmit(); })()`)
  await until(`document.querySelector('.user-create [role=alert]')`)
  assert.equal(await evaluate(`document.querySelector('.user-create-form input[type=password]').value`),'')
  usersWriteStatus = 200; usersStatus = 503
  await click('.users-list .section-heading button')
  await until(`document.querySelector('.users-list [role=alert]')`)
  assert.equal(await evaluate(`document.querySelectorAll('.managed-user').length`),0)
  usersStatus = 200
  await click('.users-list [role=alert] button')
  await until(`document.querySelectorAll('.managed-user').length === 20`)
  await click('.managed-user:nth-child(2) .user-module-access > button')
  await until(`document.querySelector('.grant-items input')`)
  grantStatus=503
  await click('.grant-content > button')
  await until(`document.querySelector('.grant-content [role=alert]')`)
  assert.equal(await evaluate(`document.querySelectorAll('.grant-items input').length`),0)
  grantStatus=200
  await click('.grant-content [role=alert] button')
  await until(`document.querySelector('.grant-items input')`)
  authenticated=true; viewer=false; admin=false
  await visit('/modules/demo')
  await until(`document.querySelector('.module-editor-form')`)
  authenticated=false
  await click('.module-audit .section-heading button')
  await until(`location.pathname === '/login' && document.querySelector('#login-password')`)
  assert.equal(await evaluate(`!document.querySelector('.sidebar, .module-editor')`),true)
  assert.equal(await evaluate(`new URLSearchParams(location.search).get('returnTo')`),'/modules/demo')
  await loadPage('Page.reload')
  await until(`document.querySelector('#login-password')`)
  await evaluate(`(() => { for (const [id,value] of [['login-username','layout-fixture'],['login-password','fixture-only-not-a-real-password']]) { const el=document.getElementById(id);el.value=value;el.dispatchEvent(new Event('input',{bubbles:true})); } document.querySelector('.login-form').requestSubmit() })()`)
  await until(`location.pathname === '/modules/demo' && document.querySelector('.module-editor-form')`)
  assert.ok(apiRequests > 0 && sessionWrites >= 6)
  console.log('CHECK inline tool state actions')
  await visit('/settings')
  await until(`document.querySelector('.tool-admin-actions button')`)
  saveStatus=409
  await evaluate(`document.querySelector('.module-list li:first-child .tool-admin-actions button').click()`)
  await until(`document.querySelector('.tool-admin-actions [role=alert]')`)
  console.log('CHECK inline conflict surfaced')
  assert.equal(module.status,'disabled')
  saveStatus=200
  await evaluate(`document.querySelector('.module-list li:first-child .tool-admin-actions button').click()`)
  await until(`document.querySelector('.module-list li:first-child .badge')?.textContent.includes('已启用')`)
  console.log('CHECK inline enable saved')
  assert.equal(module.status,'enabled')
  assert.equal(module.public_config.refresh_interval_seconds,60,'Inline status save preserves current config')
  await evaluate(`window.confirm=()=>true`)
  module.required=true
  const protectedRevision=module.revision
  await evaluate(`document.querySelector('.module-list li:first-child .tool-admin-actions button').click()`)
  await until(`document.querySelector('.tool-admin-actions [role=alert]')?.textContent.includes('不能禁用')`)
  assert.equal(module.revision,protectedRevision)
  module.required=false
  console.log('CHECK required tool protected')
  for (const width of [1440,390,360]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<761})
    authenticated=false; registrationPolicy={enabled:false,approval_required:true,revision:0}
    await visit('/register')
    await until(`document.querySelector('.register-panel')?.textContent.includes('暂未开放注册')`)
    assert.equal(await evaluate(`Boolean(document.querySelector('.register-panel input[type=password]'))`),false)
    for (registrationStatus of [404,503]) {
      await loadPage('Page.reload')
      await until(`document.querySelector('.register-panel [role=alert]')?.textContent.includes('注册服务暂不可用')`)
      assert.equal(await evaluate(`document.querySelector('.register-panel').textContent.includes('申请不存在')`),false)
      assert.equal(await evaluate(`Boolean(document.querySelector('.register-panel input[type=password]'))`),false)
    }
    registrationStatus=200
    registrationPolicy.enabled=true
    await loadPage('Page.reload')
    await until(`document.querySelector('.register-panel input[type=password]')`)
    await evaluate(`(() => { const input=document.querySelector('.register-panel input:not([type=password])');input.value='registration-candidate';input.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.register-panel input[type=password]').value=crypto.randomUUID();document.querySelector('.register-panel form').requestSubmit() })()`)
    await until(`document.querySelector('.register-panel')?.textContent.includes('申请已提交')`)
    assert.equal(authenticated,false)
    await noOverflow(); await screenshot('registration-pending-'+width)
    authenticated=true
    await visit('/settings')
    await until(`document.querySelector('.approvals li') && document.querySelector('.registration-policy fieldset')`)
    await noOverflow(); await screenshot('registration-owner-'+width)
    await evaluate(`window.confirm=()=>true`)
    await click('.approvals li button')
    await until(`document.querySelector('.approvals')?.textContent.includes('此页没有待审核')`)
    assert.equal(await evaluate(`document.querySelector('.registration-policy button[type=submit]').disabled`), true)
    await evaluate(`document.querySelector('.registration-policy input[role=switch]').focus()` )
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: ' ', code: 'Space', windowsVirtualKeyCode: 32 })
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: ' ', code: 'Space', windowsVirtualKeyCode: 32 })
    await until(`!document.querySelector('.registration-policy input[role=switch]').checked`)
    assert.equal(registrationPolicy.enabled,true, 'Switch must not save before explicit submission')
    await evaluate(`document.querySelector('.registration-policy form').requestSubmit()`)
    await until(`document.querySelector('.registration-policy [role=status]')?.textContent.includes('已保存')`)
    assert.equal(registrationPolicy.enabled,false)
    registrationStatus=503
    await click('.registration-policy .section-heading button')
    await until(`document.querySelector('.registration-policy [role=alert]')`)
    registrationStatus=200
    viewer=true
    await loadPage('Page.reload')
    await until(`document.querySelector('.settings')?.textContent.includes('仅向所有者开放')`)
    assert.equal(await evaluate(`Boolean(document.querySelector('.registration-policy, .approvals'))`),false)
    viewer=false
  }
  assert.deepEqual(errors, [])
  console.log('PASS isolated UI fixtures: anonymous deep links/reload, safe login return, expired API session redirect; public registration 404/503; registration disabled/submitted/pending, owner approval/policy save, 503 and permission boundaries at 1440/390/360; previous user/module/audit cases. No real user data used.')
  }
} finally { socket?.close(); child.kill() }

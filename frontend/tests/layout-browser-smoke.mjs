// Isolated UI fixtures: intercept every API request; never authenticate a real account.
// Run from repository root against the existing loopback Vite server.
import { spawn } from 'node:child_process'
import { writeFile, mkdir } from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
const origin = process.env.RUNTU_UI_BASE_URL || 'http://127.0.0.1:5173'
assert.ok(['http://127.0.0.1:5173', 'http://127.0.0.1:4173'].includes(origin), 'Only explicit loopback dev/preview origins are supported')
const output = path.resolve('.git/codex-coordination/task54-after', new URL(origin).port)
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
    console.log(await evaluate(`({path:location.pathname, heading:document.querySelector('h1')?.textContent, status:document.querySelector('.my-modules')?.textContent, alert:document.querySelector('[role=alert]')?.textContent,policy:document.querySelector('.registration-policy')?.textContent})`))
    throw new Error('Auth smoke condition timed out')
  }
  async function screenshot(name) {
    await until(`!document.querySelector('.auth-toast-enter-active, .auth-toast-leave-active')`)
    await evaluate(`Promise.all(document.getAnimations().filter(a=>a.effect?.getTiming().iterations!==Infinity).map(a=>a.finished.catch(()=>{}))).then(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))`)
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
  let applications = [], reviewStatus=200, reviewDetailStatus=200, reviewRequests=0
  let notificationStatus=200, notificationSendStatus=200, notificationPersonalStatus=200, notificationReads=0, notificationSends=0
  const notificationDefaults=()=>({enabled:false,revision:0,available:false,bot_mode:null,bot_username:null,personal_available:true,public_available:true,private_target:false,bound:false,destination:null,paused:false,pairing:{state:'none',expires_at:null,candidate:null},events:{registration:false,account_security:false,tool_outcomes:false,system_errors:false},supported:{registration:true,account_security:false,tool_outcomes:false,system_errors:false}})
  let notificationPrefs=notificationDefaults()
  const managedNotificationPrefs=new Map()
  let managedNotificationReads=0
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
      if(pathname.startsWith('/api/me/notifications') || pathname.startsWith('/api/admin/notifications/users/')) {
        const target=pathname.startsWith('/api/admin/notifications/users/')?pathname.split('/')[5]:null
        let prefs=target?(managedNotificationPrefs.get(target)||{...notificationDefaults(),supported:{...notificationDefaults().supported,registration:false}}):notificationPrefs
        if(target)managedNotificationReads++
        code=!authenticated?401:target&&(viewer||admin)?403:notificationStatus
        if(request.method==='GET') notificationReads++
        let connected
        if(code===200 && request.method!=='GET') {
          assert.ok(Object.keys(request.headers).some(k=>k.toLowerCase()==='x-csrf-token'))
          const value=JSON.parse(request.postData)
          for(const key of ['bot_token','chat_id','user_id'])assert.equal(value[key],undefined)
          if(value.expected_revision!==prefs.revision)code=409
          else if(pathname.endsWith('/test')){notificationSends++;code=notificationSendStatus;if(code!==200)prefs={...prefs,enabled:false,paused:true,revision:prefs.revision+1}}
          else if(pathname.endsWith('/choose-personal')&&notificationPersonalStatus!==200)code=notificationPersonalStatus
          else if(pathname.endsWith('/choose-personal')){assert.equal(value.exclusive,true);assert.ok(value.token);prefs={...notificationDefaults(),available:true,bot_mode:'personal',bot_username:'PrivateFixtureBot',revision:prefs.revision+1,supported:prefs.supported}}
          else if(pathname.endsWith('/sync-personal'))prefs={...prefs,pairing:{state:'confirm',expires_at:'2099-10-23T16:00:00Z',candidate:'••••6789'}}
          else if(pathname.endsWith('/rotate-secret'))prefs={...prefs}
          else if(pathname.endsWith('/choose-public'))prefs={...notificationDefaults(),available:true,bot_mode:'public',bot_username:'RuntuFixtureBot',revision:prefs.revision+1,supported:prefs.supported}
          else if(pathname.endsWith('/connect')){prefs={...prefs,enabled:false,private_target:false,bound:false,destination:null,revision:prefs.revision+1,pairing:{state:'waiting',expires_at:'2099-10-23T16:00:00Z',candidate:null}};connected={url:'https://t.me/'+prefs.bot_username+'?start='+'x'.repeat(43),revision:prefs.revision,expires_at:'2099-10-23T16:00:00Z'}}
          else if(pathname.endsWith('/confirm'))prefs={...prefs,bound:true,destination:'••••6789',revision:prefs.revision+1,pairing:{state:'none',expires_at:null,candidate:null}}
          else if(pathname.endsWith('/disconnect'))prefs={...notificationDefaults(),supported:prefs.supported,revision:prefs.revision+1}
          else prefs={...prefs,enabled:value.enabled,private_target:value.private_target,events:value.events,revision:prefs.revision+1}
        }
        body=code!==200?{detail:'private-upstream-diagnostic'}:connected?connected:pathname.endsWith('/test')?{state:'sent'}:{...prefs,supported:{...prefs.supported,registration:!viewer},events:{...prefs.events,registration:!viewer&&prefs.events.registration}}
        if(target)managedNotificationPrefs.set(target,prefs);else notificationPrefs=prefs
      }
      else if(pathname==='/api/admin/notifications/platform'){code=viewer||admin?403:200;body={feature_enabled:true,public_ready:true,token_present:true,username_present:true,webhook_secret_present:true,encryption_ready:true}}
      else if (pathname === '/api/health') body = { status: 'ok', platform: 'Runtu Platform', database: 'ready' }
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
        reviewRequests++
        const parts=pathname.split('/'),id=parts[4],action=parts[5],application=applications.find(row=>row.id===id)
        code=!authenticated?401:viewer||admin?403:registrationStatus
        if(id&&code===200){
          if(!application)code=404
          else if(request.method==='POST'){
            assert.ok(Object.keys(request.headers).some(k=>k.toLowerCase()==='x-csrf-token'))
            code=reviewStatus
            if(code===200&&application.state!=='pending')code=409
            if(code===200){application.state=action==='approve'?'approved':'rejected';body={state:application.state};if(action==='approve')managedUsers.push({id:application.id,username:application.username,role:'viewer',active:true,created_at:'2026-10-21T08:00:00Z'})}
          }else{code=reviewDetailStatus;body={id:application.id,username:application.username,state:application.state,created_at:'2026-10-21T08:00:00Z'}}
        }else if(code===200){
          const params=new URL(request.url).searchParams,state=params.get('state')||'pending',after=params.get('after_username')
          const rows=applications.filter(row=>row.state===state&&(after==null||row.username>after)).sort((a,b)=>a.username<b.username?-1:1)
          body={items:rows.slice(0,20).map(row=>({id:row.id,username:row.username,state:row.state})),next_after_username:rows.length>20?rows[19].username:null}
        }
        if(code!==200)body={detail:'fixture-review-error'}
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
        body = { ...user, role: invalidRole ? 'unknown' : viewer ? 'viewer' : admin ? 'admin' : 'owner', permissions: viewer ? ['platform.read', 'module.read'] : admin ? ['platform.read','module.read','module.manage','audit.read','notifications.manage'] : ['platform.read', 'module.read', 'module.manage', 'users.manage', 'audit.read', 'notifications.manage'] }
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
  async function userDirectoryChecks(capture=true) {
    async function click(selector){await evaluate(`document.querySelector(${JSON.stringify(selector)}).focus();document.querySelector(${JSON.stringify(selector)}).click()`)}
    authenticated=true;viewer=false;admin=false;usersStatus=200;usersWriteStatus=200;grantStatus=200;emptyGrantCandidates=false
    await visit('/users');await until(`document.querySelectorAll('.managed-user').length===20`)
    assert.equal(await evaluate(`!document.querySelector('.user-create-form,.user-update-form,.user-module-access')`),true)
    assert.equal(await evaluate(`document.querySelector('.directory-role').textContent`),'所有者')
    await evaluate(`document.querySelector('.directory-search input').value='no-match';document.querySelector('.directory-search input').dispatchEvent(new Event('input',{bubbles:true}))`)
    await until(`document.querySelectorAll('.managed-user').length===0`)
    await click('.directory-state button');await until(`document.querySelectorAll('.managed-user').length===20`)
    await click('[aria-label="筛选本页角色"]')
    await send('Input.dispatchKeyEvent',{type:'keyDown',key:'End',code:'End',windowsVirtualKeyCode:35})
    await send('Input.dispatchKeyEvent',{type:'keyUp',key:'End',code:'End',windowsVirtualKeyCode:35})
    await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13})
    await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13})
    await until(`document.querySelectorAll('.managed-user').length===1`)
    await click('[aria-label="筛选本页角色"]')
    await evaluate(`document.querySelector('.account-select-popup [role=option]').click()`)
    await click('.user-pagination button:last-child');await until(`document.querySelectorAll('.managed-user').length===2`)
    await click('.user-pagination button:first-child');await until(`document.querySelectorAll('.managed-user').length===20`)
    await click('.directory-create');await until(`document.querySelector('dialog')?.open`)
    assert.equal(await evaluate(`document.activeElement===document.querySelector('.user-create-form input')&&document.body.style.overflow==='hidden'`),true)
    await evaluate(`window.dispatchEvent(new Event('focus'))`)
    await until(`document.querySelector('.user-create-form') && !document.querySelector('.account-status')`)
    // Same-account revalidation must preserve the draft and modal.
    assert.equal(await evaluate(`document.querySelector('dialog').open`),true)
    // Native modal must keep sequential focus within the dialog.
    await evaluate(`document.querySelector('.user-create-form button[type=submit]').focus()`)
    await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9})
    await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9})
    assert.equal(await evaluate(`document.activeElement===document.body||document.querySelector('dialog').contains(document.activeElement)`),true)
    await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27})
    await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27})
    await until(`!document.querySelector('dialog')`)
    await until(`document.activeElement===document.querySelector('.directory-create')&&document.body.style.overflow!=='hidden'`)
    await click('.managed-user:first-child .directory-manage');await until(`document.querySelector('.user-update-form')`)
    assert.equal(await evaluate(`document.querySelector('.user-update-form fieldset').disabled`),true)
    assert.equal(await evaluate(`document.querySelector('.user-advanced').open`),false)
    await click('.dialog-close');await until(`!document.querySelector('dialog')`)
    await click('.managed-user:nth-child(2) .directory-manage');await click('#tools-tab')
    await until(`document.querySelector('.grant-items button')`)
    await click('.grant-items button');await until(`document.querySelector('.user-confirm')`)
    await click('.user-confirm button:last-child');await until(`document.querySelector('.user-module-access [role=status]')`)
    assert.equal(grantSets.get('user-fixture-0')?.has('alpha'),true)
    await click('.grant-items button');await click('.user-confirm button:last-child');await until(`document.querySelector('.grant-items small')?.textContent==='尚未授权'`)
    assert.equal(grantSets.get('user-fixture-0')?.has('alpha'),false)
    grantStatus=409;await click('.grant-items button');await click('.user-confirm button:last-child');await until(`document.querySelector('.user-module-access [role=alert]')`)
    grantStatus=503;await click('.grant-toolbar button');await until(`document.querySelector('.user-module-access [role=alert]')`)
    grantStatus=200;await click('.user-module-access [role=alert] button');await until(`document.querySelector('.grant-items button')`)
    emptyGrantCandidates=true;await click('.grant-toolbar button');await until(`document.querySelector('.grant-empty')`)
    emptyGrantCandidates=false
    await click('#account-tab');await evaluate(`document.querySelector('.user-toggle input').click();document.querySelector('.user-update-form').requestSubmit()`)
    await until(`document.querySelector('.user-confirm')`);await click('.user-confirm button:last-child');await until(`document.querySelector('.user-update-form [role=status]')`)
    assert.equal(managedUsers.find(row=>row.id==='user-fixture-0').active,false)
    // A stale/denied account update must stay an error, never success.
    usersWriteStatus=409;await evaluate(`document.querySelector('.user-toggle input').click();document.querySelector('.user-update-form').requestSubmit()`)
    await click('.user-confirm button:last-child');await until(`document.querySelector('.user-update-form [role=alert]')`)
    assert.equal(managedUsers.find(row=>row.id==='user-fixture-0').active,false)
    usersWriteStatus=403;await evaluate(`document.querySelector('.user-update-form').requestSubmit()`);await click('.user-confirm button:last-child');await until(`document.querySelector('.user-update-form [role=alert]')`)
    usersWriteStatus=200;await click('.dialog-close');await until(`!document.querySelector('dialog')`)
    await click('.directory-create');usersWriteStatus=409
    await evaluate(`(()=>{const f=document.querySelector('.user-create-form');f.querySelector('input:not([type=password])').value='fixture-new';f.querySelector('input:not([type=password])').dispatchEvent(new Event('input',{bubbles:true}));f.querySelector('input[type=password]').value=crypto.randomUUID();f.requestSubmit()})()`)
    await until(`document.querySelector('.user-create-form [role=alert]')`)
    assert.equal(await evaluate(`document.querySelector('input[type=password]').value`),'')
    usersWriteStatus=200
    await evaluate(`document.querySelector('input[type=password]').value=crypto.randomUUID();document.querySelector('.user-create-form').requestSubmit()`)
    await until(`!document.querySelector('dialog')&&document.querySelector('.directory-toast')`)
    assert.ok(managedUsers.some(row=>row.username==='fixture-new'))
    usersStatus=503;await click('.directory-refresh');await until(`document.querySelector('.user-directory [role=alert]')`)
    usersStatus=200;await click('.user-directory [role=alert] button');await until(`document.querySelectorAll('.managed-user').length===20`)
    for(const [width,height] of [[1440,900],[390,844],[360,800]]){
      await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<761})
      await visit('/users');await until(`document.querySelectorAll('.managed-user').length===20`)
      await noOverflow();if(capture)await screenshot(`users-directory-${width}`)
      await click('.directory-create');await until(`document.querySelector('dialog')?.open`)
      await noOverflow();assert.equal(await evaluate(`document.querySelector('dialog').scrollWidth<=document.querySelector('dialog').clientWidth`),true)
      if(capture)await screenshot(`users-create-${width}`)
      await click('.dialog-close');await until(`!document.querySelector('dialog')`)
      await click('.managed-user:first-child .directory-manage');await until(`document.querySelector('.user-update-form')`)
      if(capture)await screenshot(`users-manage-${width}`)
      await click('#tools-tab');await until(`document.querySelector('.grant-items button')`)
      if(capture)await screenshot(`users-grants-${width}`)
      await click('.dialog-close');await until(`!document.querySelector('dialog')`)
    }
    await click('.directory-create');viewer=true;await evaluate(`window.dispatchEvent(new Event('focus'))`);await until(`!document.querySelector('dialog')&&document.querySelector('main')?.textContent.includes('没有用户管理权限')`);viewer=false;await visit('/users');await until(`document.querySelectorAll('.managed-user').length===20`)
    const reads=userRequests
    for(const role of ['viewer','admin']){viewer=role==='viewer';admin=role==='admin';await visit('/users');await until(`document.querySelector('main')?.textContent.includes('没有用户管理权限')`);assert.equal(await evaluate(`!document.querySelector('.directory-create,dialog')`),true)}
    assert.equal(userRequests,reads);viewer=false;admin=false
    assert.deepEqual(errors,[])
    console.log('PASS user directory: modal keyboard/focus/scroll, roles, self protection, API denied/stale, create/password clearing, grant/revoke/errors/empty, pagination/search and 1440/390/360; all APIs intercepted.')
  }
  async function reviewCenterChecks(capture=true){
    await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false})
    authenticated=true;viewer=false;admin=false;registrationStatus=200;reviewStatus=200;reviewDetailStatus=200
    const key=async(key,code,virtual)=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:virtual});await send('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:virtual})}
    async function click(selector){await evaluate(`document.querySelector(${JSON.stringify(selector)}).focus();document.querySelector(${JSON.stringify(selector)}).click()`)}
    const before=reviewRequests
    await visit('/settings');await until(`document.querySelector('.registration-policy fieldset')`)
    assert.equal(reviewRequests,before,'Settings must not request registration applications')
    assert.equal(await evaluate(`!document.querySelector('.registration-directory,.approvals')`),true)
    await visit('/users');await until(`document.querySelectorAll('.managed-user').length===20`)
    assert.equal(await evaluate(`getComputedStyle(document.querySelector('.user-directory')).borderTopWidth`),'0px')
    assert.equal(await evaluate(`!document.querySelector('.users-page select')`),true)
    await click('.directory-create');await until(`document.querySelector('dialog')?.open`)
    await click('.user-create-form [role=combobox]');await until(`document.querySelector('[role=listbox]')`)
    assert.deepEqual(await evaluate(`Array.from(document.querySelectorAll('[role=option]')).map(o=>o.textContent.replace('✓','').trim())`),['普通用户','管理员','所有者'])
    await key('ArrowDown','ArrowDown',40);await key('Enter','Enter',13)
    await until(`document.querySelector('.user-create-form [role=combobox]')?.textContent.includes('管理员')`)
    assert.equal(await evaluate(`document.querySelector('.user-create-form .user-toggle input').checked`),false)
    await click('.user-create-form [role=combobox]');await key('Escape','Escape',27)
    assert.equal(await evaluate(`document.querySelector('dialog').open&&!document.querySelector('[role=listbox]')`),true)
    await click('.dialog-close');await until(`!document.querySelector('dialog')`)
    const approvedId='review-approved-fixture',rejectedId='review-rejected-fixture'
    applications=[{id:approvedId,username:'apply-alpha',state:'pending'},{id:rejectedId,username:'apply-beta',state:'pending'}]
    const actualUsers=managedUsers.length
    await click('#users-reviews-tab');await until(`document.querySelectorAll('.application-row').length===2`)
    assert.equal(managedUsers.length,actualUsers)
    await click('.application-row .directory-manage');await until(`document.querySelector('.review-detail')`)
    await evaluate(`Array.from(document.querySelectorAll('.review-detail button')).find(b=>b.textContent==='批准申请').click()`)
    reviewStatus=409;await click('.review-detail .user-confirm button:last-child');await until(`document.querySelector('.review-detail [role=alert]')`)
    assert.equal(managedUsers.length,actualUsers)
    reviewStatus=200
    await evaluate(`Array.from(document.querySelectorAll('.review-detail button')).find(b=>b.textContent==='批准申请').click()`)
    await click('.review-detail .user-confirm button:last-child');await until(`!document.querySelector('dialog')&&document.querySelectorAll('.application-row').length===1`)
    assert.equal(managedUsers.length,actualUsers+1)
    await until(`document.activeElement===document.querySelector('#users-reviews-tab')`)
    await click('.application-row .directory-manage');await until(`document.querySelector('.review-detail')`)
    await evaluate(`Array.from(document.querySelectorAll('.review-detail button')).find(b=>b.textContent==='拒绝申请').click()`)
    await click('.review-detail .user-confirm button:last-child');await until(`!document.querySelector('dialog')&&document.querySelector('.registration-directory')?.textContent.includes('暂无待审核')`)
    assert.equal(managedUsers.length,actualUsers+1)
    await click('[aria-label="筛选申请状态"]');await key('End','End',35);await key('Enter','Enter',13)
    await until(`document.querySelectorAll('.application-row').length===1&&document.querySelector('.application-state')?.textContent==='已拒绝'`)
    await click('.application-row .directory-manage');await until(`document.querySelector('.review-finished')`)
    assert.equal(await evaluate(`!Array.from(document.querySelectorAll('.review-detail button')).some(b=>b.textContent==='批准申请'||b.textContent==='拒绝申请')`),true)
    if(capture)await screenshot('users-rejected-1440')
    await click('.dialog-close');await until(`!document.querySelector('dialog')`)
    // Detail not found and storage errors must offer refresh, never review controls.
    reviewDetailStatus=404;await click('.application-row .directory-manage');await until(`document.querySelector('dialog [role=alert]')`)
    assert.equal(await evaluate(`!document.querySelector('.review-detail')`),true)
    await click('.dialog-close');await until(`!document.querySelector('dialog')`)
    reviewDetailStatus=200
    registrationStatus=503;await click('.review-toolbar .directory-refresh');await until(`document.querySelector('.registration-directory [role=alert]')`)
    registrationStatus=200;await click('.registration-directory [role=alert] button');await until(`document.querySelector('.application-row')`)
    applications=Array.from({length:22},(_,i)=>({id:`page-review-${i}`,username:`pending-${String(i).padStart(3,'0')}`,state:'pending'}))
    await click('[aria-label="筛选申请状态"]');await key('Home','Home',36);await key('Enter','Enter',13)
    await until(`document.querySelectorAll('.application-row').length===20`)
    await click('.registration-directory .user-pagination button:last-child');await until(`document.querySelectorAll('.application-row').length===2`)
    await click('.registration-directory .user-pagination button:first-child');await until(`document.querySelectorAll('.application-row').length===20`)
    for(const [width,height] of [[1440,900],[390,844],[360,800]]){
      await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<761})
      await visit('/users');await until(`document.querySelectorAll('.managed-user').length===20`)
      await noOverflow();if(capture)await screenshot(`users-flat-${width}`)
      await click('.directory-create');await click('.user-create-form [role=combobox]');await until(`document.querySelector('[role=listbox]')`)
      assert.equal(await evaluate(`(()=>{const r=document.querySelector('[role=listbox]').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight})()`),true)
      if(capture)await screenshot(`users-role-options-${width}`)
      await evaluate(`document.querySelector('.user-dialog-heading').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}))`)
      await until(`!document.querySelector('[role=listbox]')`)
      await click('.dialog-close');await until(`!document.querySelector('dialog')`)
      applications=[{id:`screen-pending-${width}`,username:'new-applicant',state:'pending'}]
      await click('#users-reviews-tab');await until(`document.querySelector('.application-row')`)
      await noOverflow();if(capture)await screenshot(`users-pending-${width}`)
      await click('.application-row .directory-manage');await until(`document.querySelector('.review-detail')`)
      if(capture)await screenshot(`users-review-${width}`)
      await click('.dialog-close');await until(`!document.querySelector('dialog')`)
      applications=[];await click('.review-toolbar .directory-refresh');await until(`document.querySelector('.registration-directory')?.textContent.includes('暂无待审核')`)
      if(capture)await screenshot(`users-review-empty-${width}`)
    }
    const reads=reviewRequests
    for(const role of ['admin','viewer']){viewer=role==='viewer';admin=role==='admin';await visit('/users');await until(`document.querySelector('main')?.textContent.includes('没有用户管理权限')`);assert.equal(await evaluate(`!document.querySelector('#users-reviews-tab,.application-row,dialog')`),true);if(capture)await screenshot(`users-forbidden-${role}`)}
    assert.equal(reviewRequests,reads)
    viewer=false;admin=false;assert.deepEqual(errors,[])
    console.log('PASS unified account/review center: owner-only approve/reject, stale/missing/service errors, separate counts and pagination, empty/rejected states, custom dropdown keyboard/Escape/outside/viewport, no Settings review fetch, 1440/390/360, admin/viewer denial.')
  }

  async function notificationChecks(capture=true) {
    async function click(selector){await evaluate(`document.querySelector(${JSON.stringify(selector)}).focus();document.querySelector(${JSON.stringify(selector)}).click()`)}
    authenticated=true;viewer=false;admin=false;notificationStatus=200;notificationSendStatus=200;notificationPrefs=notificationDefaults()
    await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false})
    for(const width of [1440,390,360]){
      await send('Emulation.setDeviceMetricsOverride',{width,height:width===1440?900:844,deviceScaleFactor:1,mobile:width<760})
      await visit('/notifications');await until(`document.querySelector('.choose-personal')`);await noOverflow()
      assert.equal(await evaluate(`!document.querySelector('.notification-fields,.notification-manager [role=combobox]')`),true)
      assert.equal(await evaluate(`document.querySelector('.notification-manager').open || document.querySelector('.platform-telegram').open`),false)
      if(capture)await screenshot('telegram-choices-'+width)
    }
    // Actionable unavailable state, with both choices truthfully disabled.
    notificationStatus=404
    await click('.refresh-notifications');await until(`document.querySelector('.telegram-setup')`)
    assert.equal(await evaluate(`document.querySelector('.telegram-setup').textContent.includes('0011_personal_telegram_bot')`),true)
    if(capture)await screenshot('telegram-deploy-needed-360')
    notificationStatus=200;await click('.refresh-notifications');await until(`!document.querySelector('.choose-personal').disabled`)
    await click('.choose-personal');await until(`document.querySelector('.personal-bot-form')`)
    notificationPersonalStatus=502
    await evaluate(`document.querySelector('#personal-bot-token').value='fixture-only-'+crypto.randomUUID();document.querySelector('#personal-bot-token').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.exclusive-control input').click();document.querySelector('.personal-bot-form').requestSubmit()`)
    await until(`document.querySelector('.notification-error')?.textContent.includes('验证或同步失败')`)
    assert.equal(await evaluate(`document.querySelector('#personal-bot-token').value`),'')
    if(capture)await screenshot('telegram-personal-retry-360')
    notificationPersonalStatus=200
    await evaluate(`document.querySelector('#personal-bot-token').value='fixture-only-'+crypto.randomUUID();document.querySelector('#personal-bot-token').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.personal-bot-form').requestSubmit()`)
    await until(`document.querySelector('.telegram-binding h4')?.textContent.includes('PrivateFixtureBot')`)
    assert.equal(await evaluate(`!document.querySelector('input[type=password]')`),true)
    await click('.telegram-connect');await until(`document.querySelector('.telegram-pair-link')`)
    assert.equal(await evaluate(`document.querySelector('.telegram-pair-link').getAttribute('rel')`),'noopener noreferrer')
    if(capture)await screenshot('telegram-personal-pairing-360')
    await click('.sync-personal');await until(`document.querySelector('.telegram-confirm')`)
    await click('.telegram-confirm');await until(`document.querySelector('.notification-fields')`)
    await evaluate(`document.querySelector('.notification-fields input[role=switch]').focus()`)
    await send('Input.dispatchKeyEvent',{type:'keyDown',key:' ',code:'Space',windowsVirtualKeyCode:32});await send('Input.dispatchKeyEvent',{type:'keyUp',key:' ',code:'Space',windowsVirtualKeyCode:32})
    await click('.notification-fields .policy-switch:nth-of-type(2) input');await click('.notification-fields .policy-switch:nth-of-type(3) input')
    await click('.notification-save');await until(`document.querySelector('.notification-success')?.textContent.includes('已保存')`)
    await click('.notification-test button');await until(`document.querySelector('.notification-success')?.textContent.includes('发送成功')`)
    await click('.rotate-secret');await until(`document.querySelector('.notification-success')?.textContent.includes('重新加密')`)
    for(const width of [1440,390,360]){
      await send('Emulation.setDeviceMetricsOverride',{width,height:width===1440?900:844,deviceScaleFactor:1,mobile:width<760})
      await visit('/notifications');await until(`document.querySelector('.notification-fields')`);await noOverflow()
      if(capture)await screenshot('telegram-personal-bound-'+width)
      await evaluate(`document.querySelector('.notification-test').scrollIntoView({block:'end'})`);await noOverflow()
      if(capture)await screenshot('telegram-personal-events-'+width)
    }
    notificationSendStatus=502;await click('.notification-test button');await until(`document.querySelector('.notification-error')?.textContent.includes('未确认发送成功')`)
    await click('.notification-section-heading button');await until(`document.querySelector('.telegram-binding')?.textContent.includes('通知已暂停')`)
    await click('.telegram-disconnect');await until(`document.querySelector('.choose-public')`)
    assert.equal(notificationPrefs.bot_mode,null);assert.equal(notificationPrefs.private_target,false)
    await click('.choose-public');await until(`document.querySelector('.telegram-connect')`)
    await click('.telegram-connect');await until(`document.querySelector('.telegram-pair-link')`)
    notificationPrefs.pairing={state:'confirm',expires_at:'2099-10-23T16:00:00Z',candidate:'••••6789'}
    await click('.notification-section-heading button');await until(`document.querySelector('.telegram-confirm')`)
    await click('.telegram-confirm');await until(`document.querySelector('.notification-fields')`)
    if(capture)await screenshot('telegram-public-bound-360')
    await click('.telegram-disconnect');await until(`document.querySelector('.choose-personal')`)
    await click('.platform-telegram summary');await until(`document.querySelector('.platform-status')`);await noOverflow()
    if(capture)await screenshot('telegram-owner-platform-360')
    await click('.platform-telegram summary')
    await click('.notification-manager summary');await until(`document.querySelector('.notification-manager [role=combobox]:not(:disabled)')`)
    await click('.notification-manager [role=combobox]');await until(`document.querySelector('[role=listbox]')`)
    await send('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowDown',code:'ArrowDown',windowsVirtualKeyCode:40})
    await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13})
    await until(`document.querySelector('.manager-note')&&document.querySelector('.choose-personal:not(:disabled)')`)
    await click('.choose-personal');await until(`document.querySelector('.personal-bot-form')`)
    await evaluate(`document.querySelector('#personal-bot-token').value='fixture-only-'+crypto.randomUUID();document.querySelector('#personal-bot-token').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.exclusive-control input').click();document.querySelector('.personal-bot-form').requestSubmit()`)
    await until(`document.querySelector('.telegram-connect')`)
    assert.equal(notificationPrefs.bot_mode,null);assert.ok([...managedNotificationPrefs.values()].some(p=>p.bot_mode==='personal'))
    await noOverflow();if(capture)await screenshot('telegram-owner-managed-360')
    await click('.telegram-disconnect');await until(`document.querySelector('.choose-personal')`)
    const reads=managedNotificationReads
    for(const role of ['viewer','admin']){
      viewer=role==='viewer';admin=role==='admin';notificationPrefs=notificationDefaults()
      await visit('/notifications');await until(`document.querySelector('.choose-public:not(:disabled)')`)
      assert.equal(await evaluate(`!document.querySelector('.owner-tools,.manager-note')`),true)
      await click('.choose-public');await until(`document.querySelector('.telegram-connect')`)
      await click('.telegram-connect');await until(`document.querySelector('.telegram-pairing')`)
      if(capture)await screenshot('telegram-'+role+'-pairing-360')
    }
    assert.equal(managedNotificationReads,reads)
    const before=notificationReads;authenticated=false;await visit('/notifications');await until(`document.querySelector('#login-username')`)
    assert.equal(notificationReads,before)
    authenticated=true;viewer=false;admin=false;notificationStatus=200;notificationSendStatus=200
    assert.deepEqual(errors,[])
    console.log('PASS usable Telegram UI: personal token clear, bind/start/sync/confirm/target/test/rotation/unlink; public proof preserved; owner secondary management/platform status; unavailable deployment checklist; admin/viewer isolation, keyboard and 1440/390/360. All API and Telegram effects mocked; groups remain unavailable.')
  }

  if(process.env.RUNTU_NOTIFICATIONS_ONLY==='1'){await notificationChecks()}
  else if(process.env.RUNTU_REVIEWS_ONLY==='1'){await reviewCenterChecks()}
  else if(process.env.RUNTU_USERS_ONLY==='1'){await userDirectoryChecks();await reviewCenterChecks()}
  else if (process.env.RUNTU_HOME_ONLY === '1') {
    for (const [width,height] of [[1440,900],[390,844],[360,800]]) {
      await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<761})
      authenticated=true;activityStatus=200;user.username='layout-fixture'
      for (const role of ['owner','admin','viewer']) {
        viewer=role==='viewer';admin=role==='admin';activityHistory=null;ownExtraRows=[];grantSets.clear()
        await visit('/')
        await until(`document.querySelector('.account-facts')?.textContent.includes(${JSON.stringify(role==='owner'?'所有者':role==='admin'?'管理员':'普通用户')}) && document.querySelector('.authorized-total strong')?.textContent==='0'`)
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
  if(!process.env.RUNTU_REGISTRATION_ONLY) {
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
    await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9})
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
    await until(`document.querySelector('.account-role')?.textContent==='所有者'`)
    assert.equal(await evaluate(`document.querySelectorAll('.sign-out').length === 1 && !document.querySelector('main .sign-out, main .identity-bar, main .access-summary')`), true)
    await noOverflow(); await screenshot(`dashboard-account-${width}`)
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 })
    await until(`document.querySelector('.user-menu') && !document.querySelector('.user-menu').open`)
    assert.equal(await evaluate(`document.activeElement.matches('.user-trigger')`), true)
    await loadPage('Page.reload')
    await until(`document.querySelector('.user-menu') && document.querySelector('.my-modules') && document.querySelector('.overview-name')`)
    assert.equal(await evaluate(`document.querySelector('h1').textContent === '首页' && document.querySelectorAll('.sidebar nav > a').length === 4 && !document.querySelector('.system-status').open`), true)
    assert.deepEqual(await evaluate(`Array.from(document.querySelectorAll('.sidebar nav > a, .tools-toggle')).map(el=>el.textContent.trim())`), ['首页','我的工具','用户管理','消息设置','全局设置'])
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
    await click('.managed-user:first-child .directory-manage')
    await until(`document.querySelector('.user-update-form')`)
    assert.equal(await evaluate(`document.querySelector('.user-update-form fieldset').disabled`),true)
    await click('#tools-tab');await until(`document.querySelector('.grant-items button')`)
    if(!grantSets.get(user.id)?.has('alpha')){await click('.grant-items button');await click('.user-confirm button:last-child');await until(`document.querySelector('.user-module-access [role=status]')`)}
    await noOverflow();await screenshot(`grant-editor-${width}`)
    await click('.dialog-close');await until(`!document.querySelector('dialog')`)
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
  assert.equal(await evaluate(`document.querySelectorAll('.sidebar nav > a').length === 2 && !document.querySelector('.system-status')`), true)
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
  assert.equal(await evaluate(`document.querySelectorAll('.sidebar nav > a').length === 3 && !document.querySelector('.sidebar a[href="/modules"]') && Boolean(document.querySelector('.sidebar a[href="/settings"]'))`), true)
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
  await userDirectoryChecks(false)
  await notificationChecks(false)
  await reviewCenterChecks(false)
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
  }
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
    await until(`document.querySelector('.registration-policy fieldset')`)
    assert.equal(await evaluate(`!document.querySelector('.approvals,.registration-directory')`),true)
    await noOverflow(); await screenshot('registration-owner-'+width)
    await evaluate(`window.confirm=()=>true`)
    await visit('/users');await until(`document.querySelector('#users-reviews-tab')`);await click('#users-reviews-tab');await until(`document.querySelector('.application-row')`);await click('.application-row .directory-manage');await until(`document.querySelector('.review-detail')`);await evaluate(`Array.from(document.querySelectorAll('.review-detail button')).find(b=>b.textContent==='批准申请').click()`);await click('.review-detail .user-confirm button:last-child');await until(`!document.querySelector('dialog')&&document.querySelector('.registration-directory')?.textContent.includes('暂无待审核')`);await visit('/settings');await until(`document.querySelector('.registration-policy fieldset')`)
    assert.equal(await evaluate(`document.querySelector('.registration-policy button[type=submit]').disabled`), true)
    await evaluate(`document.querySelector('.registration-policy input[role=switch]').focus()` )
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: ' ', code: 'Space', windowsVirtualKeyCode: 32 })
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: ' ', code: 'Space', windowsVirtualKeyCode: 32 })
    await until(`!document.querySelector('.registration-policy input[role=switch]').checked`)
    assert.equal(registrationPolicy.enabled,true, 'Switch must not save before explicit submission')
    await until(`!document.querySelector('.registration-policy button[type=submit]').disabled`)
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

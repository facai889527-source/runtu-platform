// Run only against tests/serve_auth_smoke.py and the loopback Vite server.
import { spawn } from 'node:child_process'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
const output = path.resolve('.git/codex-coordination/auth14')
const credentials = JSON.parse(await readFile(path.join(output, 'browser-credentials.json'), 'utf8'))
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
  let seq = 0
  const waiting = new Map(), errors = []
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.id) {
      const pending = waiting.get(message.id); waiting.delete(message.id)
      message.error ? pending.reject(new Error('Browser command failed')) : pending.resolve(message.result)
    }
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
    console.log('Auth fixture condition timed out; no credentials dumped.')
    throw new Error('Auth smoke condition timed out')
  }
  async function screenshot(name) {
    // Guard every capture: never record a filled password field.
    assert.equal(await evaluate(`!document.querySelector('input[type=password]')?.value`), true)
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
    await writeFile(path.join(output, name + '.png'), Buffer.from(shot.data, 'base64'))
  }
  await send('Runtime.enable'); await send('Page.enable')
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })
  await send('Page.navigate', { url: 'http://127.0.0.1:5173/login' })
  await until(`document.querySelector('#login-password') && !document.querySelector('.sidebar')`)
  await screenshot('login-desktop')
  async function submit(password) {
    // Values stay in the isolated browser and this test's memory, never console output.
    await evaluate(`(() => { for (const [id, value] of ${JSON.stringify([['login-username', credentials.username], ['login-password', password]])}) { const el = document.getElementById(id); el.value = value; el.dispatchEvent(new Event('input', {bubbles:true})); } document.querySelector('.login-form').requestSubmit(); })()`)
  }
  await submit('deliberately-incorrect-test-password')
  await until(`document.querySelector('[role=alert]')?.textContent.includes('用户名或密码不正确')`)
  assert.equal(await evaluate(`document.querySelector('#login-password').value`), '')
  await submit(credentials.password)
  await until(`location.pathname === '/' && document.querySelector('.user-name')?.textContent === 'browser-test'`)
  await until(`document.querySelector('.account-role')?.textContent.includes('所有者')`)
  assert.equal(await evaluate(`document.cookie.includes('runtu_dev_session')`), false)
  assert.equal(await evaluate(`localStorage.length`), 0)
  await evaluate(`document.querySelector('.user-trigger').click()`)
  await screenshot('authenticated-desktop')
  await screenshot('rbac-desktop')
  await send('Page.reload')
  await until(`document.querySelector('.user-name')?.textContent === 'browser-test'`)
  await evaluate(`document.querySelector('.user-trigger').click()`)
  await evaluate(`document.querySelector('.sign-out').click()`)
  await until(`location.pathname === '/login' && document.querySelector('#login-password')`)
  await send('Page.reload')
  await until(`location.pathname === '/login' && document.querySelector('#login-password')`)
  for (const [width, height] of [[390, 844], [360, 800]]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: true })
    await send('Page.navigate', { url: 'http://127.0.0.1:5173/login' })
    await until(`document.querySelector('#login-password') && !document.querySelector('#login-password').disabled`)
    assert.equal(await evaluate(`document.documentElement.scrollWidth <= innerWidth`), true)
    assert.equal(await evaluate(`document.querySelector('.login-submit').getBoundingClientRect().height >= 44`), true)
    await screenshot(`login-mobile-${width}`)
    if (width === 390) {
      await submit(credentials.password)
      await until(`document.querySelector('.account-role')?.textContent.includes('所有者') && location.pathname === '/'`)
      assert.equal(await evaluate(`document.documentElement.scrollWidth <= innerWidth`), true)
      await screenshot('rbac-mobile-390')
      await evaluate(`document.querySelector('.user-trigger').click()`)
      await evaluate(`document.querySelector('.sign-out').click()`)
      await until(`location.pathname === '/login' && document.querySelector('#login-password')`)
    }
  }
  assert.deepEqual(errors, [])
  console.log('PASS disposable auth fixture: wrong password, field clearing, login, server owner role, HttpOnly, no localStorage, reload, logout, mobile 390/360; not the real administrator')
} finally { credentials.password = ''; socket?.close(); child.kill() }

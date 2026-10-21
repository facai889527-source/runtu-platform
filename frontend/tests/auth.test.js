import test from 'node:test'
import assert from 'node:assert/strict'
import { login, logout, readIdentity } from '../src/api/auth.js'

test('session changes obtain CSRF and use same-origin cookies without persisting credentials', async () => {
  const previous = globalThis.fetch, calls = []
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options })
    return { ok: true, json: async () => url.endsWith('/csrf') ? { csrf_token: 'a'.repeat(64) }
      : { authenticated: false, user: null } }
  }
  try {
    await login('test-user', 'disposable-secret')
    await logout()
    assert.deepEqual(calls.map(call => call.url), ['/api/auth/csrf', '/api/auth/login', '/api/auth/csrf', '/api/auth/logout'])
    assert.ok(calls.every(call => call.options.credentials === 'same-origin'))
    assert.equal(calls[1].options.headers['X-CSRF-Token'], 'a'.repeat(64))
    assert.equal(calls[1].options.method, 'POST')
    assert.equal(JSON.parse(calls[1].options.body).username, 'test-user')
  } finally { globalThis.fetch = previous }
})

test('authentication failures and malformed identities cannot produce authenticated state', async () => {
  const previous = globalThis.fetch
  try {
    for (const status of [401, 403, 429, 503]) {
      globalThis.fetch = async () => ({ ok: false, status })
      await assert.rejects(readIdentity(), error => error.status === status)
    }
    globalThis.fetch = async () => ({ ok: true, json: async () => ({ authenticated: true, user: {} }) })
    await assert.rejects(readIdentity(), /格式异常/)
  } finally { globalThis.fetch = previous }
})

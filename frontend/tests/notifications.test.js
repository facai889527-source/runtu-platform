import test from 'node:test'
import assert from 'node:assert/strict'
import { readNotifications, saveNotifications, testNotifications } from '../src/api/notifications.js'
import { parseRoute, returnTarget } from '../src/navigation/history.js'

const value = () => ({ enabled: false, chat_id: '', revision: 0, token_configured: false, token_source: 'environment',
  events: { registration: false, account_security: false, tool_outcomes: false, system_errors: false },
  supported: { registration: true, account_security: false, tool_outcomes: false, system_errors: false } })

test('notification client sends only preferences and confirms test delivery with explicit server result', async () => {
  const previous = globalThis.fetch
  const calls = []
  try {
    globalThis.fetch = async (url, options) => {
      calls.push([url, options])
      return { ok: true, json: async () => url === '/api/auth/csrf' ? { csrf_token: 'a'.repeat(64) }
        : url.endsWith('/test') ? { state: 'sent' } : value() }
    }
    assert.equal((await readNotifications()).token_configured, false)
    const payload = { enabled: false, chat_id: '', events: value().events, expected_revision: 0 }
    await saveNotifications(payload)
    assert.deepEqual(await testNotifications(0), { state: 'sent' })
    const writes = calls.filter(([, options]) => options.method !== 'GET' && options.method)
    assert.equal(writes.length, 2)
    for (const [, options] of writes) { assert.equal(options.credentials, 'same-origin'); assert.equal(options.headers['X-CSRF-Token'], 'a'.repeat(64)) }
    assert.deepEqual(JSON.parse(writes[0][1].body), payload)
    assert.deepEqual(JSON.parse(writes[1][1].body), { expected_revision: 0 })
    assert.equal(parseRoute('/notifications').title, '消息设置')
    assert.equal(returnTarget('?returnTo=%2Fnotifications'), '/notifications')
  } finally { globalThis.fetch = previous }
})

test('notification contract rejects secrets, unsupported events and unknown delivery acknowledgements', async () => {
  const previous = globalThis.fetch
  try {
    for (const mutate of [v => ({ ...v, bot_token: 'fixture-private' }), v => ({ ...v, token_source: 'database' }),
      v => ({ ...v, chat_id: 'https://foreign.test' }), v => ({ ...v, chat_id: '4503599627370496' }),
      v => ({ ...v, events: { ...v.events, system_errors: true } }), v => ({ ...v, supported: { ...v.supported, tool_outcomes: true } })]) {
      globalThis.fetch = async () => ({ ok: true, json: async () => mutate(value()) })
      await assert.rejects(readNotifications(), /格式异常/)
    }
    globalThis.fetch = async url => ({ ok: true, json: async () => url === '/api/auth/csrf' ? { csrf_token: 'a'.repeat(64) } : { state: 'queued' } })
    await assert.rejects(testNotifications(0), /未确认/)
  } finally { globalThis.fetch = previous }
})

test('notification failures use safe fixed messages without displaying upstream diagnostics', async () => {
  const previous = globalThis.fetch
  try {
    for (const status of [403, 404, 409, 422, 429, 502, 503, 504]) {
      globalThis.fetch = async () => ({ ok: false, status, json: async () => ({ detail: 'fixture-private' }) })
      await assert.rejects(readNotifications(), error => error.status === status && !error.message.includes('fixture-private'))
    }
  } finally { globalThis.fetch = previous }
})

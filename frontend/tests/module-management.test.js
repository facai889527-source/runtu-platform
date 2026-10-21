import { test } from 'node:test'
import assert from 'node:assert/strict'
import { saveModule } from '../src/api/moduleManagement.js'

const value = { enabled: false, expected_revision: 0, public_config: { show_in_navigation: true, refresh_interval_seconds: null } }
test('module writes obtain proof, use same-origin PUT and preserve explicit payload', async t => {
  const calls = []
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push([url, options])
    return new Response(JSON.stringify(url.endsWith('/csrf') ? { csrf_token: 'a'.repeat(64) }
      : { id: 'demo', status: 'disabled', revision: 1, public_config: value.public_config }))
  })
  assert.equal((await saveModule('demo', value)).revision, 1)
  assert.equal(calls[0][0], '/api/auth/csrf')
  assert.equal(calls[1][0], '/api/admin/modules/demo')
  assert.equal(calls[1][1].method, 'PUT')
  assert.equal(calls[1][1].credentials, 'same-origin')
  assert.ok(calls[1][1].headers['X-CSRF-Token'])
  assert.deepEqual(JSON.parse(calls[1][1].body), value)
})
test('denied, conflict, unavailable and malformed write results never become success', async t => {
  let status = 409, result = {}
  t.mock.method(globalThis, 'fetch', async url => new Response(JSON.stringify(url.endsWith('/csrf')
    ? { csrf_token: 'a'.repeat(64) } : result), { status: url.endsWith('/csrf') ? 200 : status }))
  for (status of [401, 403, 409, 422, 503]) await assert.rejects(saveModule('demo', value), e => e.status === status)
  status = 200
  await assert.rejects(saveModule('demo', value), /无法确认/)
})

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readPolicy, readPublicPolicy, savePolicy, readPending, register, approve } from '../src/api/registration.js'

test('registration policy and submission use narrow contracts and CSRF without returning credentials', async t => {
  const calls = []
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push({ url, options })
    if (url.endsWith('/csrf')) return Response.json({ csrf_token: 'a'.repeat(64) })
    if (url.endsWith('/register')) return Response.json({ state: 'submitted' }, { status: 202 })
    if (url.endsWith('/approve')) return Response.json({ state: 'approved' })
    if (url.startsWith('/api/admin/registrations?')) return Response.json({ items: [{ id: 'fixture', username: 'candidate', state: 'pending' }], next_after_username: null })
    return Response.json({ enabled: false, approval_required: true, ...(url.startsWith('/api/admin') ? { revision: 0 } : {}) })
  })
  assert.equal((await readPublicPolicy()).enabled, false)
  assert.equal((await readPolicy()).revision, 0)
  await savePolicy({ enabled: false, approval_required: true, expected_revision: 0 })
  const password = crypto.randomUUID()
  assert.deepEqual(await register('candidate', password), { state: 'submitted' })
  const submit = calls.find(c => c.url.endsWith('/register'))
  assert.ok(submit.options.headers['X-CSRF-Token'])
  assert.equal(submit.options.credentials, 'same-origin')
  assert.equal(JSON.parse(submit.options.body).password, password)
  assert.equal((await readPending()).items[0].state, 'pending')
  assert.deepEqual(await approve('fixture'), { state: 'approved' })
})

test('registration rejects malformed policy, private fields, pagination and HTTP failures', async t => {
  let value = {}, status = 200
  t.mock.method(globalThis, 'fetch', async () => Response.json(value, { status }))
  for (value of [{ enabled: true, approval_required: true, revision: 0, secret: 'bad' }, { enabled: 'true', approval_required: true, revision: 0 }, { enabled: true, approval_required: true, revision: -1 }]) await assert.rejects(readPolicy())
  for (value of [{ items: [{ id: 'fixture', username: 'candidate', state: 'pending', password_hash: 'bad' }], next_after_username: null }, { items: [], next_after_username: 'unexpected' }]) await assert.rejects(readPending())
  for (status of [401, 403, 409, 422, 429, 503]) await assert.rejects(readPolicy(), e => e.status === status)
})

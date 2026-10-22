import { test } from 'node:test'
import assert from 'node:assert/strict'
import { sessionFetch } from '../src/api/session.js'
import { readPublicPolicy, register } from '../src/api/registration.js'

test('protected 401 expires shared session; login failure and forbidden access do not', async () => {
  const previous = globalThis.fetch, dispatch = globalThis.dispatchEvent
  let count = 0, status = 401
  globalThis.dispatchEvent = event => { assert.equal(event.type, 'runtu-session-expired'); count++ }
  globalThis.fetch = async () => new Response('{}', {status})
  try {
    await sessionFetch('/api/modules'); await sessionFetch('/api/admin/users'); assert.equal(count, 2)
    await sessionFetch('/api/auth/login'); assert.equal(count, 2)
    status = 403; await sessionFetch('/api/admin/users'); assert.equal(count, 2)
  } finally { globalThis.fetch = previous; globalThis.dispatchEvent = dispatch }
})
test('missing public registration endpoint never reports an administrator queue error', async () => {
  const previous = globalThis.fetch
  globalThis.fetch = async () => new Response('{}', {status:404})
  try { await assert.rejects(readPublicPolicy(), error => error.status === 404 && error.message.includes('注册服务暂不可用') && !error.message.includes('申请不存在')) }
  finally { globalThis.fetch = previous }
})

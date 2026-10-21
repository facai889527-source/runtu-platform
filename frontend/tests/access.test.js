import test from 'node:test'
import assert from 'node:assert/strict'
import { readAccess } from '../src/api/access.js'

test('access view uses server role and explicit permissions with same-origin credentials', async () => {
  const previous = globalThis.fetch
  try {
    globalThis.fetch = async (url, options) => {
      assert.equal(url, '/api/admin/me')
      assert.equal(options.credentials, 'same-origin')
      return { ok: true, json: async () => ({ id: 'test', username: 'member', role: 'viewer', permissions: ['platform.read', 'module.read'], ignored: 'not rendered' }) }
    }
    assert.deepEqual(await readAccess(), { role: 'viewer', permissions: ['platform.read', 'module.read'] })
  } finally { globalThis.fetch = previous }
})

test('access failures or unknown role/permission cannot become a displayed grant', async () => {
  const previous = globalThis.fetch
  try {
    for (const status of [401, 403, 503]) {
      globalThis.fetch = async () => ({ ok: false, status })
      await assert.rejects(readAccess(), error => error.status === status)
    }
    for (const changes of [{ role: 'superuser' }, { permissions: ['*'] }, { permissions: 'module.manage' }]) {
      globalThis.fetch = async () => ({ ok: true, json: async () => ({ id: 'test', username: 'member', role: 'viewer', permissions: [], ...changes }) })
      await assert.rejects(readAccess(), /格式异常/)
    }
  } finally { globalThis.fetch = previous }
})

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { filterModules, moduleCounts } from '../src/utils/modules.js'
import { readHealth, readModule } from '../src/api/client.js'
import { useResource } from '../src/composables/useResource.js'
const items = [
  { id: 'demo', name: '演示模块', description: '演示', status: 'enabled', category: null, capabilities: [] },
  { id: 'tools', name: '工具', description: '维护', status: 'disabled', category: 'TOOLS', capabilities: ['inspect'] },
]
test('search combines status, category, capabilities, case and whitespace', () => {
  assert.deepEqual(filterModules(items, ' tools ', 'disabled'), [items[1]])
  assert.deepEqual(filterModules(items, 'INSPECT', 'enabled'), [])
  assert.deepEqual(filterModules(items, '演示', 'all'), [items[0]])
  assert.deepEqual(moduleCounts(items), { total: 2, enabled: 1, disabled: 1 })
  assert.deepEqual(moduleCounts([]), { total: 0, enabled: 0, disabled: 0 })
})
test('health preserves degraded 503 and details expose 404/503 without raw server errors', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({status:'degraded',platform:'Runtu',database:'unavailable'}), {status:503}))
  assert.equal((await readHealth()).database, 'unavailable')
  await assert.rejects(readModule('demo'), (error) => error.status === 503)
  globalThis.fetch = async () => new Response('{}', {status:404})
  await assert.rejects(readModule('missing'), (error) => error.status === 404)
})
test('latest result wins even when previous reader ignores abort', async () => {
  const resolvers = []
  const resource = useResource(() => new Promise((resolve) => resolvers.push(resolve)))
  const old = resource.load(), current = resource.load()
  resolvers[1]('new'); await current
  resolvers[0]('old'); await old
  assert.equal(resource.data.value, 'new')
  assert.equal(resource.pending.value, false)
})
test('cancellation prevents late updates and retry clears errors', async () => {
  let resolve
  const resource = useResource(() => new Promise((done) => { resolve = done }))
  const request = resource.load(); resource.cancel(); resolve('late'); await request
  assert.equal(resource.data.value, null)
  let attempt = 0
  const retry = useResource(async () => { if (!attempt++) throw new Error('offline'); return [] })
  await retry.load(); assert.equal(retry.error.value.message, 'offline')
  await retry.load(); assert.deepEqual(retry.data.value, []); assert.equal(retry.error.value, null)
})

test('retained identity survives an in-flight check but clears on failure', async () => {
  let resolve, reject
  const resource = useResource(() => new Promise((yes,no) => { resolve=yes; reject=no }), {retainData:true})
  resource.data.value = {authenticated:true}
  const first = resource.load()
  assert.equal(resource.data.value.authenticated,true)
  resolve({authenticated:true}); await first
  const second = resource.load()
  assert.equal(resource.data.value.authenticated,true)
  reject(new Error('unavailable')); await second
  assert.equal(resource.data.value,null)
  assert.equal(resource.error.value.message,'unavailable')
})

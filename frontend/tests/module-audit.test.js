import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readModuleAudit } from '../src/api/moduleAudit.js'

const item = revision => ({ module_id: 'demo', actor_id: 'fixture-actor', action: 'updated', created_at: '2026-10-21T08:00:00Z', revision })
test('audit reads fixed bounded query with same-origin credentials and forwards cancellation', async t => {
  const signal = new AbortController().signal
  t.mock.method(globalThis,'fetch',async (url,options) => {
    assert.equal(url,'/api/admin/modules/demo/changes?limit=10&before_revision=11')
    assert.equal(options.method,'GET'); assert.equal(options.credentials,'same-origin'); assert.equal(options.signal,signal)
    return Response.json({items:[item(10)],next_before_revision:null})
  })
  assert.equal((await readModuleAudit('demo',11,signal)).items[0].revision,10)
})
test('audit rejects malformed, unordered, wrong-module and unbounded pages',async t => {
  let page
  t.mock.method(globalThis,'fetch',async () => Response.json(page))
  for (page of [{}, {items:[{...item(1),session:'not-renderable'}],next_before_revision:null},
    {items:[item(1),item(2)],next_before_revision:null}, {items:[{...item(1),module_id:'other'}],next_before_revision:null},
    {items:[item(1)],next_before_revision:1}, {items:[{...item(1),created_at:'invalid'}],next_before_revision:null},
    {items:[item(11)],next_before_revision:null}, {items:Array.from({length:11},(_,i)=>item(11-i)),next_before_revision:null}]) {
    await assert.rejects(readModuleAudit('demo',11),/格式异常/)
  }
  await assert.rejects(readModuleAudit('demo',0),/分页位置/)
  page={items:[],next_before_revision:null}
  assert.deepEqual(await readModuleAudit('demo'),page)
  page={items:Array.from({length:10},(_,i)=>item(10-i)),next_before_revision:1}
  assert.equal((await readModuleAudit('demo')).next_before_revision,1)
})
test('audit surfaces permission and service failures without echoing server diagnostics',async t => {
  let status
  t.mock.method(globalThis,'fetch',async () => Response.json({detail:'private-server-detail'},{status}))
  for (status of [401,403,404,422,503]) await assert.rejects(readModuleAudit('demo'),e=>e.status===status&&!e.message.includes('private-server-detail'))
})

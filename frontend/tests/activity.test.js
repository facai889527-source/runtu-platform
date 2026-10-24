import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readLoginActivity } from '../src/api/auth.js'

test('own login activity uses cookies and accepts absent or UTC server history only', async () => {
  const original=globalThis.fetch
  try {
    for(const previous_login of [null,{at:'2026-10-22T08:45:00+00:00',ip:'198.51.100.24'},{at:'2026-10-22T08:45:00Z',ip:null}]) {
      globalThis.fetch=async (path,options)=>{assert.equal(path,'/api/auth/activity');assert.equal(options.credentials,'same-origin');return Response.json({previous_login})}
      assert.deepEqual(await readLoginActivity(),{previous_login})
    }
    for(const data of [{previous_login:null,token:'private'}, {previous_login:{at:'invalid',ip:null}}, {previous_login:{at:'2026-10-22T08:45:00Z',ip:'<private>'}}, {previous_login:{at:'2026-10-22T08:45:00Z',ip:null,user_id:'another'}},{}]) {
      globalThis.fetch=async()=>Response.json(data)
      await assert.rejects(readLoginActivity())
    }
    globalThis.fetch=async()=>Response.json({private:'not-for-display'},{status:503})
    await assert.rejects(readLoginActivity(),error=>error.status===503&&!error.message.includes('not-for-display'))
  } finally {globalThis.fetch=original}
})

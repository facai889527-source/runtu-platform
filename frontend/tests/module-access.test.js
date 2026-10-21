import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readMyModules,readUserModules,saveUserModule } from '../src/api/moduleAccess.js'
const row={module_id:'alpha',name:'受保护模块',enabled:true,granted:true}
test('module access reads own or owner target summary, writes with security proof',async t=>{
  const calls=[]
  t.mock.method(globalThis,'fetch',async(url,options)=>{
    calls.push({url,options})
    return Response.json(url.includes('/csrf')?{csrf_token:'a'.repeat(64)}:options.method==='PUT'?row:{items:[row],next_after_module:null})
  })
  assert.equal((await readMyModules()).items[0].module_id,'alpha')
  assert.equal(calls[0].url,'/api/me/modules?limit=20')
  await readUserModules('fixture-id')
  assert.equal(calls[1].url,'/api/admin/users/fixture-id/modules?limit=20')
  assert.deepEqual(await saveUserModule('fixture-id','alpha',{granted:true,expected_granted:false}),row)
  assert.equal(calls.at(-1).options.method,'PUT')
  assert.equal(calls.at(-1).options.credentials,'same-origin')
  assert.ok(calls.at(-1).options.headers['X-CSRF-Token'])
})
test('own module summary rejects ungranted/disabled/unknown fields, owner may see disabled grants',async t=>{
  let value={items:[row],next_after_module:null},status=200
  t.mock.method(globalThis,'fetch',async()=>Response.json(value,{status}))
  for(value of [{items:[{...row,granted:false}],next_after_module:null},{items:[{...row,enabled:false}],next_after_module:null},{items:[{...row,private:'not-rendered'}],next_after_module:null}])await assert.rejects(readMyModules())
  value={items:[{...row,enabled:false}],next_after_module:null}
  assert.equal((await readUserModules('fixture')).items[0].enabled,false)
  for(status of [401,403,409,422,503])await assert.rejects(readMyModules(),e=>e.status===status)
})

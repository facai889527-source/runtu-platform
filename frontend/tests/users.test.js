import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readUsers, createUser, updateUser } from '../src/api/users.js'
const row={id:'fixture-id',username:'example',role:'viewer',active:true,created_at:'2026-10-21T08:00:00Z'}
test('user reads are bounded and writes obtain proof without returning the submitted password',async t=>{
  const calls=[]
  const password='disposable-'+Math.random().toString(36)
  t.mock.method(globalThis,'fetch',async(url,options)=>{
    calls.push({url,options})
    return Response.json(url.includes('/csrf')?{csrf_token:'a'.repeat(64)}:options.method==='POST'||options.method==='PATCH'?row:{items:[row],next_after_username:null})
  })
  assert.deepEqual((await readUsers()).items,[row])
  assert.equal(calls[0].url,'/api/admin/users?limit=20')
  assert.equal(calls[0].options.credentials,'same-origin')
  const created=await createUser('example',password,'viewer')
  assert.equal(JSON.stringify(created).includes(password),false)
  assert.equal(calls[2].options.method,'POST'); assert.ok(calls[2].options.headers['X-CSRF-Token'])
  const value={role:'viewer',active:false,expected_role:'viewer',expected_active:true}
  await updateUser(row.id,value)
  assert.equal(calls.at(-1).options.method,'PATCH'); assert.deepEqual(JSON.parse(calls.at(-1).options.body),value)
})
test('user API rejects secret fields, malformed identity, pagination and server failures',async t=>{
  let response={items:[row],next_after_username:null},status=200
  t.mock.method(globalThis,'fetch',async()=>Response.json(response,{status}))
  for(response of [{items:[{...row,password_hash:'forbidden'}],next_after_username:null},{items:[{...row,username:null}],next_after_username:null},{items:[row],next_after_username:'bad'},{items:Array(21).fill(row),next_after_username:null}]) await assert.rejects(readUsers())
  for(status of [401,403,409,422,503]) await assert.rejects(readUsers(),e=>e.status===status)
})

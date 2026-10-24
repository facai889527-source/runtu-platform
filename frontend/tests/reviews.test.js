import test from 'node:test'
import assert from 'node:assert/strict'
import { readApplications,readApplication,reject } from '../src/api/registration.js'
test('owner review uses distinct application state, narrow detail and CSRF reject contract',async t=>{
 const calls=[]
 t.mock.method(globalThis,'fetch',async(url,options)=>{calls.push({url,options});if(url.endsWith('/csrf'))return Response.json({csrf_token:'a'.repeat(64)});if(url.endsWith('/reject'))return Response.json({state:'rejected'});if(url.includes('?'))return Response.json({items:[{id:'review-fixture',username:'candidate',state:'rejected'}],next_after_username:null});return Response.json({id:'review-fixture',username:'candidate',state:'pending',created_at:'2026-10-23T00:00:00Z'})})
 assert.equal((await readApplications('rejected')).items[0].state,'rejected')
 assert.equal(new URL(calls[0].url,'https://fixture.test').searchParams.get('state'),'rejected')
 assert.equal((await readApplication('review-fixture')).state,'pending')
 assert.deepEqual(await reject('review-fixture'),{state:'rejected'})
 const write=calls.find(c=>c.url.endsWith('/reject'));assert.equal(write.options.method,'POST');assert.equal(write.options.credentials,'same-origin');assert.ok(write.options.headers['X-CSRF-Token']);assert.equal(write.options.body,undefined)
})
test('review clients reject mixed state, private fields and unknown outcomes',async t=>{
 let value
 t.mock.method(globalThis,'fetch',async url=>Response.json(url.endsWith('/csrf')?{csrf_token:'a'.repeat(64)}:value))
 for(value of [{items:[{id:'fixture',username:'candidate',state:'approved'}],next_after_username:null},{items:[],next_after_username:null,password_hash:'private'},{items:[],next_after_username:'invalid'}])await assert.rejects(readApplications('pending'))
 for(value of [{id:'other',username:'candidate',state:'pending',created_at:'2026-10-23T00:00:00Z'},{id:'fixture',username:'candidate',state:'unknown',created_at:'2026-10-23T00:00:00Z'},{id:'fixture',username:'candidate',state:'pending',created_at:'2026-10-23T00:00:00Z',password:'private'}])await assert.rejects(readApplication('fixture'))
 for(value of [{state:'approved'},{state:'rejected',secret:'private'}])await assert.rejects(reject('fixture'))
 await assert.rejects(readApplications('approved'))
})

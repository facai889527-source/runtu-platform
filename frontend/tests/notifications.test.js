import test from 'node:test'
import assert from 'node:assert/strict'
import { readNotifications, saveNotifications, testNotifications, connectTelegram, confirmTelegram, disconnectTelegram, choosePublicBot, choosePersonalBot, syncPersonalBot, rotatePersonalSecret, readTelegramPlatform, initializeTelegram } from '../src/api/notifications.js'
import { parseRoute, returnTarget } from '../src/navigation/history.js'
const value=()=>({enabled:false,revision:0,available:false,bot_mode:null,bot_username:null,personal_available:true,public_available:true,private_target:false,owner_account:false,bound:false,destination:null,paused:false,pairing:{state:'none',expires_at:null,candidate:null},events:{registration:false,account_security:false,tool_outcomes:false,system_errors:false},supported:{registration:false,account_security:false,tool_outcomes:false,system_errors:false}})

test('self notification requests never carry target user or chat and use CSRF for pairing and delivery',async()=>{
 const previous=globalThis.fetch,calls=[]
 try{
  globalThis.fetch=async(url,options)=>{calls.push([url,options]);return{ok:true,json:async()=>url==='/api/auth/csrf'?{csrf_token:'a'.repeat(64)}:url.endsWith('/connect')?{url:'https://t.me/RuntuFixtureBot?start='+'x'.repeat(43),expires_at:'2026-10-23T16:00:00Z',revision:1}:url.endsWith('/test')?{state:'sent'}:value()}}
  await readNotifications();await saveNotifications({enabled:false,events:value().events,expected_revision:0});await connectTelegram(0);await confirmTelegram(1);await disconnectTelegram(2);await testNotifications(3)
  for(const [url,options]of calls.filter(([,o])=>o.method&&o.method!=='GET')){assert.ok(url.startsWith('/api/me/notifications'));assert.equal(options.credentials,'same-origin');assert.equal(options.headers['X-CSRF-Token'],'a'.repeat(64));assert.equal(JSON.parse(options.body).user_id,undefined);assert.equal(JSON.parse(options.body).chat_id,undefined)}
  assert.equal(parseRoute('/notifications').title,'消息设置');assert.equal(returnTarget('?returnTo=%2Fnotifications'),'/notifications')
 }finally{globalThis.fetch=previous}
})
test('notification client rejects secret fields, leaked destinations and unsafe pairing URLs',async()=>{
 const previous=globalThis.fetch
 try{
  for(const mutate of [v=>({...v,bot_token:'private-fixture'}),v=>({...v,destination:'123456789'}),v=>({...v,chat_id:'1234'}),v=>({...v,events:{...v.events,system_errors:true}}),v=>({...v,pairing:{state:'confirm',expires_at:'invalid',candidate:'12345'}})]){
   globalThis.fetch=async()=>({ok:true,json:async()=>mutate(value())});await assert.rejects(readNotifications(),/格式异常/)
  }
  for(const url of ['https://foreign.test/?start=x','javascript:alert(1)','https://t.me/RuntuFixtureBot?start=x&target=other']){
   globalThis.fetch=async p=>({ok:true,json:async()=>p==='/api/auth/csrf'?{csrf_token:'a'.repeat(64)}:{url,expires_at:'2026-10-23T16:00:00Z',revision:1}});await assert.rejects(connectTelegram(0),/未确认/)
  }
 }finally{globalThis.fetch=previous}
})
test('self notification failures use safe messages and never invent delivery confirmation',async()=>{
 const previous=globalThis.fetch
 try{
  for(const status of [403,404,409,422,429,502,503,504]){globalThis.fetch=async()=>({ok:false,status,json:async()=>({detail:'private-fixture'})});await assert.rejects(readNotifications(),e=>e.status===status&&!e.message.includes('private-fixture'))}
  globalThis.fetch=async p=>({ok:true,json:async()=>p==='/api/auth/csrf'?{csrf_token:'a'.repeat(64)}:{state:'queued'}});await assert.rejects(testNotifications(0),/未确认/)
 }finally{globalThis.fetch=previous}
})


test('owner notification scope uses an explicit path, encodes no target in self payload and rejects malformed scope',async()=>{
 const previous=globalThis.fetch,calls=[]
 try{
  globalThis.fetch=async(url,options)=>{calls.push([url,options]);return{ok:true,json:async()=>url==='/api/auth/csrf'?{csrf_token:'a'.repeat(64)}:value()}}
  await readNotifications(undefined,'fixture-target')
  await choosePublicBot(0,undefined,'fixture-target')
  await disconnectTelegram(1,undefined,'fixture-target')
  assert.ok(calls.filter(([url])=>url!=='/api/auth/csrf').every(([url])=>url.startsWith('/api/admin/notifications/users/fixture-target')))
  for(const target of ['../self','?target=other','x'.repeat(37)])await assert.rejects(readNotifications(undefined,target),/范围无效/)
 }finally{globalThis.fetch=previous}
})

test('unbound or unverified DTO cannot imply selected routes or enabled delivery',async()=>{
 const previous=globalThis.fetch
 try{
  for(const patch of [{bot_mode:'unknown'},{enabled:true},{private_target:true},{available:'true'},{public_available:null}]){
   globalThis.fetch=async()=>({ok:true,json:async()=>({...value(),...patch})})
   await assert.rejects(readNotifications(),/格式异常/)
  }
 }finally{globalThis.fetch=previous}
})


test('personal Bot uses protected scoped POST; responses reject ciphertext and platform secrets',async()=>{
 const previous=globalThis.fetch,calls=[]
 try{
  const safe={...value(),bot_mode:'personal',bot_username:'PrivateFixtureBot',available:true}
  globalThis.fetch=async(url,options)=>{calls.push([url,options]);return{ok:true,json:async()=>url==='/api/auth/csrf'?{csrf_token:'a'.repeat(64)}:safe}}
  await choosePersonalBot('fixture-only-secret',true,0,undefined,'fixture-target')
  await syncPersonalBot(1,undefined,'fixture-target');await rotatePersonalSecret(1,undefined,'fixture-target')
  const writes=calls.filter(([url])=>url.includes('/api/admin/notifications/users/'))
  assert.equal(writes.length,3)
  for(const [,options]of writes){assert.equal(options.method,'POST');assert.equal(options.headers['X-CSRF-Token'],'a'.repeat(64));assert.equal(options.credentials,'same-origin')}
  assert.equal(JSON.parse(writes[0][1].body).token,'fixture-only-secret')
  for(const extra of [{token:'leak'},{ciphertext:'leak'},{update_offset:1}]){
   globalThis.fetch=async url=>({ok:true,json:async()=>url==='/api/auth/csrf'?{csrf_token:'a'.repeat(64)}:{...safe,...extra}})
   await assert.rejects(syncPersonalBot(1),/格式异常/)
  }
  globalThis.fetch=async()=>({ok:true,json:async()=>({feature_enabled:true,public_ready:false,token_present:false,username_present:false,webhook_secret_present:false,encryption_ready:true,token:'leak'})})
  await assert.rejects(readTelegramPlatform(),/状态未确认/)
 }finally{globalThis.fetch=previous}
})


test('owner setup uses CSRF without key material and validates owner DTO',async()=>{
 const previous=globalThis.fetch,calls=[]
 try{
  globalThis.fetch=async(url,options)=>{calls.push([url,options]);return {ok:true,json:async()=>url==='/api/auth/csrf'?{csrf_token:'a'.repeat(64)}:{...value(),owner_account:true}}}
  const result=await initializeTelegram();assert.equal(result.owner_account,true)
  const [url,options]=calls.at(-1);assert.equal(url,'/api/admin/notifications/setup');assert.equal(options.method,'POST');assert.equal(options.credentials,'same-origin');assert.equal(options.headers['X-CSRF-Token'],'a'.repeat(64));assert.deepEqual(JSON.parse(options.body),{expected_revision:0})
  globalThis.fetch=async()=>({ok:true,json:async()=>({...value(),owner_account:'owner'})});await assert.rejects(readNotifications(),/格式异常/)
 }finally{globalThis.fetch=previous}
})


test('full verified identity is scoped and typed; legacy DTO has no invented identity or custom capability',async()=>{
 const previous=globalThis.fetch
 const identity={user_id:'123456789',chat_id:'123456789',first_name:'<b>Plain</b>',last_name:null,username:null,display_name:'<b>Plain</b>'}
 const extended={...value(),bot_mode:'public',bound:true,destination:'••••6789',identity,candidate_identity:null,custom_test_available:true}
 try{
  globalThis.fetch=async()=>({ok:true,json:async()=>extended});assert.deepEqual((await readNotifications()).identity,identity)
  for(const bad of [{...identity,user_id:123456789},{...identity,user_id:'123456788'},{...identity,token:'private'},{...identity,username:'<script>'}]){
   globalThis.fetch=async()=>({ok:true,json:async()=>({...extended,identity:bad})});await assert.rejects(readNotifications(),/身份格式异常/)
  }
  globalThis.fetch=async()=>({ok:true,json:async()=>value()});const legacy=await readNotifications();assert.equal(legacy.identity,null);assert.equal(legacy.custom_test_available,false)
 }finally{globalThis.fetch=previous}
})

test('custom test text and confirmed immutable candidate use protected scoped requests, with no recipient override',async()=>{
 const previous=globalThis.fetch,calls=[]
 try{
  globalThis.fetch=async(url,options)=>{calls.push([url,options]);return{ok:true,json:async()=>url==='/api/auth/csrf'?{csrf_token:'a'.repeat(64)}:url.endsWith('/test')?{state:'sent'}:value()}}
  await testNotifications(4,undefined,'fixture-target','<b>plain</b> & 第二行')
  assert.deepEqual(JSON.parse(calls.at(-1)[1].body),{expected_revision:4,message:'<b>plain</b> & 第二行'})
  assert.equal(calls.at(-1)[0],'/api/admin/notifications/users/fixture-target/test')
  await confirmTelegram(5,undefined,undefined,'123456789')
  assert.deepEqual(JSON.parse(calls.at(-1)[1].body),{expected_revision:5,candidate_user_id:'123456789'})
 }finally{globalThis.fetch=previous}
})

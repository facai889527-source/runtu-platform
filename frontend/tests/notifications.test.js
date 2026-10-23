import test from 'node:test'
import assert from 'node:assert/strict'
import { readNotifications, saveNotifications, testNotifications, connectTelegram, confirmTelegram, disconnectTelegram, choosePublicBot } from '../src/api/notifications.js'
import { parseRoute, returnTarget } from '../src/navigation/history.js'
const value=()=>({enabled:false,revision:0,available:false,bot_mode:null,public_available:true,private_target:false,bound:false,destination:null,paused:false,pairing:{state:'none',expires_at:null,candidate:null},events:{registration:false,account_security:false,tool_outcomes:false,system_errors:false},supported:{registration:false,account_security:false,tool_outcomes:false,system_errors:false}})

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
  for(const patch of [{bot_mode:'personal'},{enabled:true},{private_target:true},{available:'true'},{public_available:null}]){
   globalThis.fetch=async()=>({ok:true,json:async()=>({...value(),...patch})})
   await assert.rejects(readNotifications(),/格式异常/)
  }
 }finally{globalThis.fetch=previous}
})

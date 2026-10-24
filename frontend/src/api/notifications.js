import { sessionFetch } from './session.js'
import { ApiError } from './client.js'
import { securityHeaders } from './auth.js'

const path = '/api/me/notifications'
const events = ['registration','account_security','tool_outcomes','system_errors']
const exact = (v,keys) => v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === keys.length && keys.every(k=>Object.hasOwn(v,k))
const date = v => typeof v === 'string' && Number.isFinite(Date.parse(v))
export function preferences(v) {
  if (!exact(v,['enabled','revision','available','bound','destination','paused','pairing','events','supported','bot_mode','bot_username','personal_available','public_available','private_target','owner_account'])
    || ['enabled','available','bound','paused','public_available','personal_available','private_target','owner_account'].some(k=>typeof v[k]!=='boolean')
    || ![null,'public','personal'].includes(v.bot_mode)
    || !(v.bot_username===null || (typeof v.bot_username==='string' && /^[A-Za-z][A-Za-z0-9_]{1,28}[Bb][Oo][Tt]$/.test(v.bot_username))) || (v.bot_mode===null && (v.bound || v.enabled || v.private_target || v.pairing?.state!=='none'))
    || (v.private_target && !v.bound) || (v.enabled && !v.private_target)
    || !Number.isInteger(v.revision) || v.revision<0 || v.revision>2147483646
    || !(v.destination===null || /^••••[0-9]{1,4}$/.test(v.destination)) || (v.bound !== (v.destination!==null))
    || !exact(v.pairing,['state','expires_at','candidate']) || !['none','waiting','confirm'].includes(v.pairing.state)
    || !(v.pairing.state==='none' ? v.pairing.expires_at===null && v.pairing.candidate===null : date(v.pairing.expires_at))
    || !(v.pairing.state==='confirm' ? /^••••[0-9]{1,4}$/.test(v.pairing.candidate) : v.pairing.candidate===null)
    || !exact(v.events,events) || !exact(v.supported,events)
    || events.some(k=>typeof v.events[k]!=='boolean'||typeof v.supported[k]!=='boolean'||(v.events[k]&&!v.supported[k]))
    || events.slice(1).some(k=>v.supported[k])) throw new Error('个人消息设置格式异常，请刷新。')
  return v
}
async function request(suffix,method,value,signal,target) {
  if(target && (typeof target!=='string' || target.length>36 || !/^[A-Za-z0-9-]+$/.test(target))) throw new Error('账户范围无效。')
  const scoped=target?`/api/admin/notifications/users/${encodeURIComponent(target)}`:path
  const headers=method==='GET'?{Accept:'application/json'}:await securityHeaders(signal)
  const r=await sessionFetch(scoped+suffix,{method,signal,credentials:'same-origin',headers,...(value===undefined?{}:{body:JSON.stringify(value)})})
  if(!r.ok) throw new ApiError(r.status,{
    401:'登录已失效，请重新登录。',403:'身份或安全校验已失效，请刷新身份。',404:'当前后端尚未部署消息接口，请按下方步骤部署后重试。',
    409:'配置已变化，或 Bot 已被其他账户、Webhook 或轮询占用。请刷新；不要接管其他部署。',422:suffix==='/choose-personal'?'Token 格式或专用控制确认无效，请重新核对 BotFather 提供的 Token。':'请先选择 Bot、完成私聊验证并选择接收目标；检查服务端启用状态。',
    429:'操作已限流，请五分钟后重试。',502:suffix==='/test'?'未确认发送成功，通知可能已暂停。请刷新并检查机器人是否被屏蔽。':'Telegram 验证或同步失败，请检查 Bot Token、网络和原部署状态。',
    503:'消息服务暂不可用，可能需要部署、迁移或配置加密密钥。请查看下方启用步骤。',504:'发送结果未确认，请勿立即重试。',
  }[r.status]||'操作结果未确认，请刷新。')
  return r.json()
}
export const readNotifications=async (signal,target)=>preferences(await request('','GET',undefined,signal,target))
export const saveNotifications=async (v,signal,target)=>preferences(await request('','PUT',v,signal,target))
export async function connectTelegram(revision,signal,target) {
  const v=await request('/connect','POST',{expected_revision:revision},signal,target)
  if(!exact(v,['url','expires_at','revision']) || !date(v.expires_at) || !Number.isInteger(v.revision)
    || typeof v.url!=='string' || !/^https:\/\/t\.me\/[A-Za-z][A-Za-z0-9_]{1,28}[Bb][Oo][Tt]\?start=[A-Za-z0-9_-]{43}$/.test(v.url)) throw new Error('配对链接未确认，请重新连接。')
  return v
}
export const confirmTelegram=async (revision,signal,target)=>preferences(await request('/confirm','POST',{expected_revision:revision},signal,target))
export const disconnectTelegram=async (revision,signal,target)=>preferences(await request('/disconnect','POST',{expected_revision:revision},signal,target))
export async function testNotifications(revision,signal,target) {
  const v=await request('/test','POST',{expected_revision:revision},signal,target)
  if(!exact(v,['state'])||v.state!=='sent') throw new Error('发送结果未确认，请勿立即重试。')
  return v
}

export const choosePublicBot=async (revision,signal,target)=>preferences(await request('/choose-public','POST',{expected_revision:revision},signal,target))

export const choosePersonalBot=async (token,exclusive,revision,signal,target)=>preferences(await request('/choose-personal','POST',{token,exclusive,expected_revision:revision},signal,target))
export const syncPersonalBot=async (revision,signal,target)=>preferences(await request('/sync-bot','POST',{expected_revision:revision},signal,target))
export const rotatePersonalSecret=async (revision,signal,target)=>preferences(await request('/rotate-secret','POST',{expected_revision:revision},signal,target))
export async function readTelegramPlatform(signal){
 const r=await sessionFetch('/api/admin/notifications/platform',{signal,credentials:'same-origin',headers:{Accept:'application/json'}})
 if(!r.ok)throw new ApiError(r.status,'需部署/启用：请按清单检查服务端，配置值不会在页面展示。')
 const v=await r.json(),keys=['feature_enabled','public_ready','token_present','username_present','webhook_secret_present','encryption_ready']
 if(!exact(v,keys)||keys.some(k=>typeof v[k]!=='boolean'))throw new Error('平台状态未确认，请检查部署。')
 return v
}

export async function initializeTelegram(signal){
 const r=await sessionFetch('/api/admin/notifications/setup',{method:'POST',signal,credentials:'same-origin',headers:await securityHeaders(signal),body:JSON.stringify({expected_revision:0})})
 if(!r.ok)throw new ApiError(r.status,'安全存储尚未就绪，初始化未确认。请刷新状态后联系维护人员处理。')
 return preferences(await r.json())
}

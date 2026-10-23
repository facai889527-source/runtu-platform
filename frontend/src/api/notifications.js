import { sessionFetch } from './session.js'
import { ApiError } from './client.js'
import { securityHeaders } from './auth.js'

const path = '/api/admin/notifications/telegram'
const eventKeys = ['registration', 'account_security', 'tool_outcomes', 'system_errors']
function exact(value, keys) {
  return value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === keys.length && keys.every(k => Object.hasOwn(value, k))
}
function preferences(value) {
  if (!exact(value, ['enabled', 'chat_id', 'revision', 'token_configured', 'token_source', 'events', 'supported'])
      || typeof value.enabled !== 'boolean' || typeof value.token_configured !== 'boolean' || value.token_source !== 'environment'
      || typeof value.chat_id !== 'string' || (value.chat_id !== '' && (!/^-?[1-9][0-9]{0,18}$/.test(value.chat_id) || Math.abs(Number(value.chat_id)) >= 2**52))
      || !Number.isInteger(value.revision) || value.revision < 0 || value.revision > 2147483646
      || !exact(value.events, eventKeys) || !exact(value.supported, eventKeys)
      || eventKeys.some(k => typeof value.events[k] !== 'boolean' || typeof value.supported[k] !== 'boolean' || (value.events[k] && !value.supported[k]))
      || !value.supported.registration || eventKeys.slice(1).some(k => value.supported[k])) throw new Error('消息设置格式异常，请刷新后重试。')
  return value
}
async function request(suffix, method, value, signal) {
  const headers = method === 'GET' ? { Accept: 'application/json' } : await securityHeaders(signal)
  const response = await sessionFetch(path + suffix, { method, signal, credentials: 'same-origin', headers,
    ...(value === undefined ? {} : { body: JSON.stringify(value) }) })
  if (!response.ok) throw new ApiError(response.status, {
    401: '登录已失效，请重新登录。', 403: '消息设置权限或安全校验已失效，请刷新身份。',
    404: '消息服务尚未启用，请联系平台维护人员。', 409: '消息设置已变化，请刷新后重新确认。',
    422: '配置不完整或 Chat ID 格式无效，请检查后保存。', 429: '测试发送已限流，请五分钟后再试。',
    502: 'Telegram 未确认发送成功，请检查机器人权限与 Chat ID。',
    503: '消息设置暂不可用，请联系平台维护人员确认服务。', 504: '发送结果未确认，请勿立即重复发送。',
  }[response.status] || '操作结果未确认，请刷新设置。')
  return response.json()
}
export const readNotifications = async signal => preferences(await request('', 'GET', undefined, signal))
export const saveNotifications = async (value, signal) => preferences(await request('', 'PUT', value, signal))
export async function testNotifications(revision, signal) {
  const value = await request('/test', 'POST', { expected_revision: revision }, signal)
  if (!exact(value, ['state']) || value.state !== 'sent') throw new Error('发送结果未确认，请勿立即重复发送。')
  return value
}

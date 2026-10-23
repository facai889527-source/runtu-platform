import { sessionFetch } from './session.js'
import { ApiError } from './client.js'
import { securityHeaders } from './auth.js'

async function request(path, signal, method = 'GET', value) {
  const headers = method === 'GET' ? { Accept: 'application/json' } : await securityHeaders(signal)
  const response = await sessionFetch(path, { signal, credentials: 'same-origin', method, headers,
    ...(value === undefined ? {} : { body: JSON.stringify(value) }) })
  if (!response.ok) throw new ApiError(response.status, {
    401: '请重新登录。', 403: '注册未开放、身份无权操作或安全校验失效，请刷新确认。',
    404: path.startsWith('/api/auth/') ? '注册服务暂不可用，请联系管理员确认后重试。' : '申请不存在，请刷新列表。', 409: '策略或审核状态已变化，请刷新后重新确认。',
    422: '格式无效：用户名需3至64位小写字母、数字或 _.-，密码需14至128位。',
    429: '提交过于频繁，请等待五分钟后重试。', 503: '注册服务暂不可用，请稍后重试。',
  }[response.status] || '操作失败，请刷新确认结果。')
  return response.json()
}
function policy(value, owner) {
  const keys = owner ? ['enabled','approval_required','revision'] : ['enabled','approval_required']
  if (!value || Object.keys(value).length !== keys.length || keys.some(k => !(k in value))
    || typeof value.enabled !== 'boolean' || typeof value.approval_required !== 'boolean'
    || (owner && (!Number.isInteger(value.revision) || value.revision < 0 || value.revision > 2147483646))) throw new Error('注册策略格式异常。')
  return value
}
export const readPublicPolicy = async signal => policy(await request('/api/auth/registration-policy', signal), false)
export const readPolicy = async signal => policy(await request('/api/admin/registration-policy', signal), true)
export const savePolicy = async (value, signal) => policy(await request('/api/admin/registration-policy', signal, 'PUT', value), true)
export async function register(username, password, signal) {
  const value = await request('/api/auth/register', signal, 'POST', { username, password })
  if (value?.state !== 'submitted' || Object.keys(value).length !== 1) throw new Error('提交结果未确认，请联系管理员。')
  return value
}
export async function readApplications(state, after, signal) {
  if (!['pending','rejected'].includes(state)) throw new Error('审核状态无效。')
  const query = new URLSearchParams({ limit: '20', state })
  if (after != null) query.set('after_username', after)
  const value = await request(`/api/admin/registrations?${query}`, signal)
  if (!value || Object.keys(value).length!==2 || !('next_after_username' in value) || !Array.isArray(value.items) || value.items.length > 20) throw new Error('申请列表格式异常。')
  value.items.forEach((v, i) => {
    if (Object.keys(v).length !== 3 || typeof v.id !== 'string' || !v.id || v.id.length > 36
      || !/^[a-z0-9_.-]{3,64}$/.test(v.username) || v.state !== state
      || (after != null && v.username <= after) || (i && v.username <= value.items[i-1].username)) throw new Error('申请数据格式异常。')
  })
  if (!(value.next_after_username === null || (value.items.length === 20 && value.next_after_username === value.items.at(-1).username))) throw new Error('申请分页格式异常。')
  return value
}
export async function approve(id, signal) {
  const value = await request(`/api/admin/registrations/${encodeURIComponent(id)}/approve`, signal, 'POST')
  if (value?.state !== 'approved' || Object.keys(value).length !== 1) throw new Error('批准结果未确认，请刷新列表。')
  return value
}

export const readPending = (after, signal) => readApplications('pending', after, signal)
export async function readApplication(id, signal) {
  const value=await request(`/api/admin/registrations/${encodeURIComponent(id)}`, signal)
  if(!value || Object.keys(value).length!==4 || value.id!==id || typeof value.username!=='string'
    || !/^[a-z0-9_.-]{3,64}$/.test(value.username) || !['pending','approved','rejected'].includes(value.state)
    || typeof value.created_at!=='string' || !Number.isFinite(Date.parse(value.created_at))) throw new Error('申请详情格式异常，请刷新。')
  return value
}
export async function reject(id, signal) {
  const value=await request(`/api/admin/registrations/${encodeURIComponent(id)}/reject`, signal, 'POST')
  if(value?.state!=='rejected' || Object.keys(value).length!==1) throw new Error('拒绝结果未确认，请刷新列表。')
  return value
}

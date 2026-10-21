import { ApiError } from './client.js'
import { securityHeaders } from './auth.js'

const fields = ['id', 'username', 'role', 'active', 'created_at']
function user(value) {
  if (!value || Object.keys(value).length !== fields.length || fields.some(key => !(key in value))
    || typeof value.id !== 'string' || !value.id || value.id.length > 36
    || typeof value.username !== 'string' || !/^[a-z0-9_.-]{3,64}$/.test(value.username) || !['owner','admin','viewer'].includes(value.role)
    || typeof value.active !== 'boolean' || typeof value.created_at !== 'string' || !Number.isFinite(Date.parse(value.created_at))) throw new Error('用户数据格式异常，请重新加载。')
  return value
}
async function result(response) {
  if (!response.ok) throw new ApiError(response.status, {
    401: '登录已失效，请重新登录。', 403: '没有用户管理权限，或操作被安全保护拒绝。',
    404: '用户不存在，请刷新列表。', 409: '用户名已存在或用户状态已变化，请刷新后确认。',
    413: '提交内容过长。', 422: '格式无效：用户名需3至64位小写字母、数字或 _.-，密码需14至128位。',
    503: '用户服务暂不可用，请稍后重试。',
  }[response.status] || '用户操作失败，请重试。')
  return response.json()
}
export async function readUsers(after, signal) {
  const query = new URLSearchParams({ limit: '20' })
  if (after != null) query.set('after_username', after)
  const page = await result(await fetch(`/api/admin/users?${query}`, { signal, credentials: 'same-origin', headers: { Accept: 'application/json' } }))
  if (!Array.isArray(page.items) || page.items.length > 20) throw new Error('用户列表格式异常。')
  page.items.forEach((item,index) => { user(item); if ((after != null && item.username <= after) || (index && item.username <= page.items[index-1].username)) throw new Error('用户列表顺序异常。') })
  if (!(page.next_after_username === null || (page.items.length === 20 && page.next_after_username === page.items.at(-1).username))) throw new Error('用户分页格式异常。')
  return { items: page.items, next_after_username: page.next_after_username }
}
async function write(path, method, value, signal) {
  const headers = await securityHeaders(signal)
  return user(await result(await fetch(path, { method, credentials: 'same-origin', signal, headers, body: JSON.stringify(value) })))
}
export const createUser = (username, password, role, signal) => write('/api/admin/users', 'POST', { username, password, role }, signal)
export const updateUser = (id, value, signal) => write(`/api/admin/users/${encodeURIComponent(id)}`, 'PATCH', value, signal)

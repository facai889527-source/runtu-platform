import { ApiError } from './client.js'

const roles = new Set(['owner', 'admin', 'viewer'])
const permissions = new Set(['platform.read', 'module.read', 'module.manage', 'users.manage', 'audit.read'])
export async function readAccess(signal) {
  const response = await fetch('/api/admin/me', { signal, credentials: 'same-origin', headers: { Accept: 'application/json' } })
  if (!response.ok) throw new ApiError(response.status, response.status === 401
    ? '登录已失效，请重新确认身份。' : response.status === 403 ? '当前身份没有访问权限。' : '权限信息暂不可用。')
  const data = await response.json()
  if (!roles.has(data?.role) || typeof data.id !== 'string' || typeof data.username !== 'string'
      || !Array.isArray(data.permissions) || data.permissions.some(value => !permissions.has(value))) throw new Error('权限接口返回格式异常。')
  // Only explicit server fields flow into the view. This list never authorizes requests.
  return { role: data.role, permissions: data.permissions }
}

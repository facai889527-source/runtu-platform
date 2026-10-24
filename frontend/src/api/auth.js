import { sessionFetch } from './session.js'
import { ApiError } from './client.js'

async function request(path, signal, options = {}) {
  const response = await sessionFetch(`/api/auth/${path}`, { credentials: 'same-origin', signal,
    ...options, headers: { Accept: 'application/json', ...options.headers } })
  if (!response.ok) throw new ApiError(response.status,
    response.status === 401 ? '用户名或密码不正确。' :
    response.status === 429 ? '尝试过于频繁，请等待五分钟后重试。' :
    response.status === 403 ? '安全校验未通过，请刷新页面后重试。' :
    response.status === 503 ? '认证服务暂不可用，请稍后重试。' : '认证请求失败，请稍后重试。')
  return response.json()
}

function identity(data) {
  if (typeof data?.authenticated !== 'boolean' || (data.authenticated
    ? typeof data.user?.id !== 'string' || typeof data.user?.username !== 'string' || typeof data.user?.is_admin !== 'boolean'
    : data.user !== null)) throw new Error('身份接口返回格式异常。')
  return data
}

export async function readIdentity(signal) { return identity(await request('me', signal)) }

export async function securityHeaders(signal) {
  // This proof stays in this request's memory. The browser owns the HttpOnly cookie.
  const csrf = await request('csrf', signal)
  if (!/^[0-9a-f]{64}$/.test(csrf?.csrf_token)) throw new Error('安全校验数据异常。')
  return { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf.csrf_token }
}

async function changeSession(path, data, signal) {
  const headers = await securityHeaders(signal)
  return identity(await request(path, signal, { method: 'POST',
    headers,
    body: JSON.stringify(data) }))
}

export const login = (username, password, signal) => changeSession('login', { username, password }, signal)
export const logout = (signal) => changeSession('logout', {}, signal)

export async function readLoginActivity(signal) {
  const response = await sessionFetch('/api/auth/activity', { credentials: 'same-origin', signal, headers: { Accept: 'application/json' } })
  if (!response.ok) throw new ApiError(response.status, '登录记录暂不可用，请稍后重试。')
  const data = await response.json(), previous = data?.previous_login
  if (!data || Object.keys(data).length !== 1 || !Object.hasOwn(data, 'previous_login') || (previous !== null &&
    (!previous || Object.keys(previous).sort().join(',') !== 'at,ip' || typeof previous.at !== 'string' ||
    !/Z$|[+]00:00$/.test(previous.at) || !Number.isFinite(Date.parse(previous.at)) ||
    !(previous.ip === null || (typeof previous.ip === 'string' && previous.ip.length <= 45 && /^[0-9a-f:.]+$/i.test(previous.ip)))))) throw new Error('登录记录格式异常。')
  return data
}

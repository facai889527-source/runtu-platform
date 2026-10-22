import { sessionFetch } from './session.js'
export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status }
}
export async function readJson(path, signal, { health = false } = {}) {
  const response = await sessionFetch(path, { signal, headers: { Accept: 'application/json' } })
  if (!response.ok && !(health && response.status === 503)) throw new ApiError(response.status, response.status === 404 ? '模块不存在或已移除。' : response.status === 503 ? '模块公开配置暂不可用，请检查数据库后重试。' : '读取失败，请稍后重试。')
  const data = await response.json()
  if (health && (!['ok', 'degraded'].includes(data.status) || !['not_configured', 'ready', 'unavailable'].includes(data.database) || typeof data.platform !== 'string')) throw new Error('健康接口返回格式异常。')
  return data
}
export const readHealth = (signal) => readJson('/api/health', signal, { health: true })
export async function readModules(signal) {
  const data = await readJson('/api/modules', signal)
  if (!Array.isArray(data)) throw new Error('模块列表格式异常。')
  return data
}
export const readModule = (id, signal) => readJson(`/api/modules/${encodeURIComponent(id)}`, signal)

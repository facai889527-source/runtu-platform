import { sessionFetch } from './session.js'
import { ApiError } from './client.js'
import { securityHeaders } from './auth.js'

export async function saveModule(id, value, signal) {
  const headers = await securityHeaders(signal)
  const response = await sessionFetch(`/api/admin/modules/${encodeURIComponent(id)}`, {
    method: 'PUT', credentials: 'same-origin', signal, headers, body: JSON.stringify(value),
  })
  if (!response.ok) throw new ApiError(response.status, {
    401: '登录已失效，请重新登录。', 403: '没有工具管理权限，或安全校验未通过。',
    404: '工具已移除，请返回目录。', 409: '工具已被其他操作更新，请重新加载后再编辑。',
    422: '配置格式不正确，请检查刷新间隔。', 503: '工具存储暂不可用，请确认数据库迁移后重试。',
  }[response.status] || '保存失败，请稍后重试。')
  const result = await response.json()
  if (result?.id !== id || !['enabled', 'disabled'].includes(result.status)
    || !Number.isInteger(result.revision) || result.revision < 0
    || typeof result.public_config?.show_in_navigation !== 'boolean'
    || !(result.public_config.refresh_interval_seconds === null || (Number.isInteger(result.public_config.refresh_interval_seconds)
      && result.public_config.refresh_interval_seconds >= 1 && result.public_config.refresh_interval_seconds <= 86400))) throw new Error('保存结果无法确认，请重新加载工具。')
  return result
}

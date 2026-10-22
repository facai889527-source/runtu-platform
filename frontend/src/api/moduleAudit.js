import { sessionFetch } from './session.js'
import { ApiError } from './client.js'

export async function readModuleAudit(id, beforeRevision, signal) {
  const query = new URLSearchParams({ limit: '10' })
  if (beforeRevision != null) {
    if (!Number.isInteger(beforeRevision) || beforeRevision < 1 || beforeRevision > 2147483647) throw new Error('记录分页位置无效，请刷新。')
    query.set('before_revision', String(beforeRevision))
  }
  const response = await sessionFetch(`/api/admin/modules/${encodeURIComponent(id)}/changes?${query}`, {
    method: 'GET', credentials: 'same-origin', signal, headers: { Accept: 'application/json' },
  })
  if (!response.ok) throw new ApiError(response.status, {
    401: '登录已失效，请重新登录后查看。', 403: '当前身份没有查看操作记录的权限。',
    404: '模块已移除，请返回目录。', 422: '记录分页位置无效，请刷新。',
    503: '操作记录暂不可用，请稍后重试。',
  }[response.status] || '操作记录加载失败，请重试。')
  const page = await response.json()
  const fields = ['module_id', 'actor_id', 'action', 'created_at', 'revision']
  const items = page?.items
  if (!Array.isArray(items) || items.length > 10 || items.some((item, index) =>
    !item || Object.keys(item).length !== fields.length || fields.some(key => !(key in item))
    || item.module_id !== id || typeof item.actor_id !== 'string' || !item.actor_id || item.actor_id.length > 36
    || item.action !== 'updated' || !Number.isInteger(item.revision) || item.revision < 1 || item.revision > 2147483647
    || (beforeRevision != null && item.revision >= beforeRevision)
    || (index > 0 && item.revision >= items[index - 1].revision)
    || typeof item.created_at !== 'string' || !/(Z|\+00:00)$/.test(item.created_at) || !Number.isFinite(Date.parse(item.created_at)))
    || !(page.next_before_revision === null || (items.length === 10 && page.next_before_revision === items.at(-1).revision))) {
    throw new Error('操作记录返回格式异常，请重试。')
  }
  return { items, next_before_revision: page.next_before_revision }
}

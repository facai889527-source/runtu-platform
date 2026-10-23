export function filterModules(modules, query, status) {
  const needle = query.trim().toLocaleLowerCase()
  return modules.filter((item) => (status === 'all' || item.status === status) &&
    [item.id, item.name, item.category || '', item.description, ...(item.capabilities || [])].join(' ').toLocaleLowerCase().includes(needle))
}
export function moduleCounts(modules) {
  return { total: modules.length, enabled: modules.filter((m) => m.status === 'enabled').length, disabled: modules.filter((m) => m.status === 'disabled').length }
}
export const databaseLabels = {
  not_configured: '未配置数据库 · 公开配置使用工具默认值。',
  ready: '数据库可用 · 本次配置存储检查通过。',
  unavailable: '数据库不可用 · 服务降级，请检查连接与迁移。',
}

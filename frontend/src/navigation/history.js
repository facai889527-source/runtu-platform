const moduleIdPattern = /^[a-z][a-z0-9_]{0,63}$/

export function modulePath(id) {
  if (typeof id !== 'string' || !moduleIdPattern.test(id)) throw new Error('Invalid module ID')
  return `/modules/${encodeURIComponent(id)}`
}

export function parseRoute(pathname) {
  const path = pathname.length > 1 ? pathname.replace(/\/$/, '') : pathname
  const pages = {
    '/': { page: 'dashboard', title: '仪表盘' },
    '/modules': { page: 'modules', title: '模块管理' },
    '/settings': { page: 'settings', title: '设置' },
    '/users': { page: 'users', title: '用户管理' },
    '/login': { page: 'login', title: '管理员登录' },
  }
  if (Object.hasOwn(pages, path)) return { ...pages[path], path, moduleId: null }
  const match = /^\/modules\/([^/]+)$/.exec(path)
  if (match) {
    try {
      const moduleId = decodeURIComponent(match[1])
      if (moduleIdPattern.test(moduleId)) return { page: 'modules', title: '模块详情', path, moduleId }
    } catch { /* Malformed encoding belongs to the route 404, never the API. */ }
  }
  return { page: 'not-found', title: '页面不存在', path, moduleId: null }
}

// A small History API adapter: only same-origin absolute paths are navigable.
// An injected browser also makes history/listener behavior testable without a DOM.
export function createNavigation(browser) {
  const listeners = new Set()
  const current = () => parseRoute(browser.location.pathname)
  function publish() { for (const listener of listeners) listener(current()) }
  browser.addEventListener('popstate', publish)
  return {
    current,
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener) },
    navigate(path) {
      if (typeof path !== 'string' || !path.startsWith('/') || path.startsWith('//') || path.includes('\\')) throw new Error('Only local paths are allowed')
      const url = new URL(path, browser.location.origin)
      if (url.origin !== browser.location.origin) throw new Error('Only local paths are allowed')
      const destination = `${url.pathname}${url.search}${url.hash}`
      const previous = `${browser.location.pathname}${browser.location.search}${browser.location.hash}`
      if (destination !== previous) browser.history.pushState(null, '', destination)
      publish()
    },
    dispose() { browser.removeEventListener('popstate', publish); listeners.clear() },
  }
}

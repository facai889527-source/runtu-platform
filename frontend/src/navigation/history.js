const moduleIdPattern = /^[a-z][a-z0-9_]{0,63}$/

export function modulePath(id) {
  if (typeof id !== 'string' || !moduleIdPattern.test(id)) throw new Error('Invalid module ID')
  return `/modules/${encodeURIComponent(id)}`
}

export function parseRoute(pathname) {
  const path = pathname.length > 1 ? pathname.replace(/\/$/, '') : pathname
  const pages = {
    '/': { page: 'dashboard', title: '首页' },
    '/tools': { page: 'tools', title: '我的工具' },
    '/modules': { page: 'modules', title: '全局设置' },
    '/settings': { page: 'settings', title: '全局设置' },
    '/users': { page: 'users', title: '用户管理' },
    '/login': { page: 'login', title: '管理员登录' },
    '/register': { page: 'register', title: '申请账户' },
  }
  if (Object.hasOwn(pages, path)) return { ...pages[path], path, moduleId: null }
  const match = /^\/modules\/([^/]+)$/.exec(path)
  if (match) {
    try {
      const moduleId = decodeURIComponent(match[1])
      if (moduleIdPattern.test(moduleId)) return { page: 'modules', title: '工具详情', path, moduleId }
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
    navigate(path, { replace = false } = {}) {
      if (typeof path !== 'string' || !path.startsWith('/') || path.startsWith('//') || path.includes('\\')) throw new Error('Only local paths are allowed')
      const url = new URL(path, browser.location.origin)
      if (url.origin !== browser.location.origin) throw new Error('Only local paths are allowed')
      const destination = `${url.pathname}${url.search}${url.hash}`
      const previous = `${browser.location.pathname}${browser.location.search}${browser.location.hash}`
      if (destination !== previous) browser.history[replace ? 'replaceState' : 'pushState'](null, '', destination)
      publish()
    },
    dispose() { browser.removeEventListener('popstate', publish); listeners.clear() },
  }
}

// Return targets are known workspace routes only; never external URLs or auth loops.
export function returnTarget(search) {
  const value = new URLSearchParams(search).get('returnTo')
  if (!value || !value.startsWith('/') || value.startsWith('//') || value.includes('\\') || value.includes('?') || value.includes('#')) return '/'
  const route = parseRoute(value)
  return ['dashboard', 'tools', 'modules', 'settings', 'users'].includes(route.page) ? route.path : '/'
}
export const loginPath = path => '/login?returnTo=' + encodeURIComponent(path)

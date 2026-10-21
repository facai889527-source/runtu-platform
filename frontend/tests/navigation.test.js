import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseRoute, modulePath, createNavigation } from '../src/navigation/history.js'

test('known pages, encoded detail, trailing slash and route 404', () => {
  assert.equal(parseRoute('/').page, 'dashboard')
  assert.equal(parseRoute('/modules/').title, '模块管理')
  assert.equal(parseRoute('/settings').page, 'settings')
  assert.equal(parseRoute('/users/').page, 'users')
  assert.equal(parseRoute('/register').page, 'register')
  assert.equal(parseRoute('/modules/%64emo').moduleId, 'demo')
  assert.equal(parseRoute('/modules/missing').title, '模块详情')
  for (const path of ['/unknown','/modules/demo/extra','/modules/%','/modules/%2f%2fevil.test','/modules/..','/modules/a%5Cb','/modules/中文','/modules/'+ 'a'.repeat(65)]) assert.equal(parseRoute(path).page, 'not-found', path)
  assert.equal(modulePath('demo_2'), '/modules/demo_2')
  for (const id of ['https://evil.test', '../demo', 'a/b', '', 'Demo', null, undefined]) assert.throws(() => modulePath(id))
})

function fakeBrowser() {
  const events = new Map(), entries = ['http://localhost/']
  let index = 0
  return {
    get location() { return new URL(entries[index]) },
    addEventListener(name, callback) { events.set(name, callback) },
    removeEventListener(name, callback) { if (events.get(name) === callback) events.delete(name) },
    history: {
      pushState(_state, _unused, path) { entries.splice(++index); entries.push(new URL(path, entries[index - 1]).href) },
      back() { if (index) { index--; events.get('popstate')?.() } },
      forward() { if (index < entries.length - 1) { index++; events.get('popstate')?.() } },
      get length() { return entries.length },
    },
    events,
  }
}

test('push/back/forward update route, same destination does not duplicate, cleanup removes listener', () => {
  const browser = fakeBrowser(), navigation = createNavigation(browser), paths = []
  const unsubscribe = navigation.subscribe((route) => paths.push(route.path))
  navigation.navigate('/modules'); navigation.navigate('/modules/demo'); navigation.navigate('/modules/demo')
  assert.equal(browser.history.length, 3)
  browser.history.back(); assert.equal(navigation.current().path, '/modules')
  browser.history.forward(); assert.equal(navigation.current().moduleId, 'demo')
  navigation.navigate('/absent'); assert.equal(navigation.current().page, 'not-found')
  assert.deepEqual(paths, ['/modules','/modules/demo','/modules/demo','/modules','/modules/demo','/absent'])
  unsubscribe(); navigation.dispose(); assert.equal(browser.events.size, 0)
})

test('navigation never accepts an external origin or backslash path', () => {
  const browser = fakeBrowser(), navigation = createNavigation(browser)
  for (const path of ['https://evil.test', '//evil.test', '/\\evil.test', 'javascript:alert(1)', null]) assert.throws(() => navigation.navigate(path))
  assert.equal(browser.history.length, 1)
  navigation.dispose()
})

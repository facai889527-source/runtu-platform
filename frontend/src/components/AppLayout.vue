<script setup>
import { ref, computed, nextTick, watch, onMounted, onUnmounted, useTemplateRef } from 'vue'
import RouteLink from './RouteLink.vue'
import AppIcon from './AppIcon.vue'
import BrandMark from './BrandMark.vue'
const props = defineProps({ page: String, title: String, path: String, platform: String, canManageUsers: Boolean, canManageSettings: Boolean })
defineEmits(['refresh'])
const collapsed = ref(false), mobileOpen = ref(false)
const sidebar = useTemplateRef('sidebar'), menu = useTemplateRef('menu'), content = useTemplateRef('content')
const entries = computed(() => [
  { id: 'dashboard', path: '/', name: '首页', icon: 'dashboard' },
  { id: 'tools', path: '/tools', name: '我的工具', icon: 'module' },
  ...(props.canManageUsers ? [{ id: 'users', path: '/users', name: '用户管理', icon: 'lock' }] : []),
  ...(props.canManageSettings ? [{ id: 'settings', path: '/settings', name: '全局设置', icon: 'settings' }] : []),
])
const description = computed(() => ({ tools: '查看已授权的工具。', modules: '维护平台模块与公开配置。', users: '管理账户、角色与工具访问权限。', settings: '管理你有权限访问的平台功能。' }[props.page] || ''))
function isCurrent(entry) { return pageId() === entry.id }
function pageId() { return props.page === 'modules' && props.canManageSettings ? 'settings' : props.page }
const media = window.matchMedia('(max-width: 760px)')
const isMobile = ref(media.matches)
function resize() { isMobile.value = media.matches; mobileOpen.value = false }
async function close() { mobileOpen.value = false; await nextTick(); menu.value?.focus() }
async function focusPage() {
  mobileOpen.value = false
  await nextTick()
  content.value?.focus({ preventScroll: true })
  window.scrollTo(0, 0)
}
watch(() => [props.path, props.title, props.platform], () => {
  document.title = `${props.title} · ${props.platform}`
})
watch(() => props.path, focusPage)
async function open() { mobileOpen.value = true; await nextTick(); sidebar.value?.querySelector('button')?.focus() }
function keyboard(event) {
  if (!mobileOpen.value) return
  if (event.key === 'Escape') { event.preventDefault(); close() }
  if (event.key === 'Tab') {
    const items = [...sidebar.value.querySelectorAll('button, a[href]')].filter((el) => el.getClientRects().length)
    const first = items[0], last = items.at(-1)
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
  }
}
watch(mobileOpen, (value) => { document.body.style.overflow = value ? 'hidden' : '' })
onMounted(() => { document.title = `${props.title} · ${props.platform}`; focusPage(); media.addEventListener('change', resize); document.addEventListener('keydown', keyboard) })
onUnmounted(() => { media.removeEventListener('change', resize); document.removeEventListener('keydown', keyboard); document.body.style.overflow = '' })
</script>
<template>
  <div class="shell" :class="{ collapsed, 'mobile-open': mobileOpen }">
    <a href="#main-content" class="skip">跳到主要内容</a>
    <button v-if="mobileOpen" class="scrim" aria-label="关闭导航" tabindex="-1" @click="close" />
    <aside id="navigation" ref="sidebar" class="sidebar" :inert="isMobile && !mobileOpen" :role="isMobile && mobileOpen ? 'dialog' : undefined" :aria-modal="isMobile && mobileOpen ? true : undefined" aria-label="平台导航">
      <div class="brand"><BrandMark /><span class="nav-label brand-word">Runtu<span class="brand-sub">多功能工具平台</span></span></div>
      <button class="mobile-only drawer-close" @click="close"><AppIcon name="close" />关闭导航</button>
      <nav aria-label="主导航"><RouteLink v-for="entry in entries" :key="entry.id" :to="entry.path" :aria-label="entry.name" :title="entry.name" :aria-current="isCurrent(entry) ? 'page' : undefined" @navigate="focusPage"><AppIcon :name="entry.icon" /><span class="nav-label">{{ entry.name }}</span></RouteLink></nav>
      <div class="sidebar-foot"><button class="desktop-only collapse-button" :aria-expanded="!collapsed" aria-controls="navigation" :aria-label="collapsed ? '展开侧栏' : '折叠侧栏'" @click="collapsed = !collapsed"><AppIcon :name="collapsed ? 'right' : 'left'" :size="18" /><span class="nav-label">折叠侧栏</span></button></div>
    </aside>
    <div class="workspace" :inert="mobileOpen">
      <header class="toolbar"><div class="toolbar-title"><button ref="menu" class="mobile-only icon-button" aria-label="打开导航" :aria-expanded="mobileOpen" aria-controls="navigation" @click="open"><AppIcon name="menu" /></button></div><div class="toolbar-actions"><button class="refresh-button" aria-label="刷新数据" title="刷新数据" @click="$emit('refresh')"><AppIcon name="refresh" :size="16" /></button><slot name="account" /></div></header>
      <main id="main-content" ref="content" tabindex="-1"><div class="page-intro"><h1>{{ title }}</h1><p v-if="description">{{ description }}</p></div><slot /></main>
      <footer><span>Runtu Platform</span></footer>
    </div>
  </div>
</template>

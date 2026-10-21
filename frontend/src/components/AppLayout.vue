<script setup>
import { ref, computed, nextTick, watch, onMounted, onUnmounted, useTemplateRef } from 'vue'
const props = defineProps({ page: String, connection: String, platform: String })
const emit = defineEmits(['navigate', 'refresh'])
const collapsed = ref(false), mobileOpen = ref(false)
const sidebar = useTemplateRef('sidebar'), menu = useTemplateRef('menu'), content = useTemplateRef('content')
const entries = [{ id: 'dashboard', name: '仪表盘', symbol: '▦' }, { id: 'modules', name: '模块管理', symbol: '◫' }, { id: 'settings', name: '设置', symbol: '⚙' }]
const title = computed(() => entries.find((e) => e.id === props.page)?.name)
const media = window.matchMedia('(max-width: 760px)')
const isMobile = ref(media.matches)
function resize() { isMobile.value = media.matches; mobileOpen.value = false }
async function close() { mobileOpen.value = false; await nextTick(); menu.value?.focus() }
async function navigate(id) { emit('navigate', id); mobileOpen.value = false; await nextTick(); content.value?.focus() }
async function open() { mobileOpen.value = true; await nextTick(); sidebar.value?.querySelector('button')?.focus() }
function keyboard(event) {
  if (!mobileOpen.value) return
  if (event.key === 'Escape') { event.preventDefault(); close() }
  if (event.key === 'Tab') {
    const items = [...sidebar.value.querySelectorAll('button')].filter((el) => el.getClientRects().length)
    const first = items[0], last = items.at(-1)
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
  }
}
watch(mobileOpen, (value) => { document.body.style.overflow = value ? 'hidden' : '' })
onMounted(() => { media.addEventListener('change', resize); document.addEventListener('keydown', keyboard) })
onUnmounted(() => { media.removeEventListener('change', resize); document.removeEventListener('keydown', keyboard); document.body.style.overflow = '' })
</script>
<template>
  <div class="shell" :class="{ collapsed, 'mobile-open': mobileOpen }">
    <a href="#main-content" class="skip">跳到主要内容</a>
    <button v-if="mobileOpen" class="scrim" aria-label="关闭导航" tabindex="-1" @click="close" />
    <aside id="navigation" ref="sidebar" class="sidebar" :inert="isMobile && !mobileOpen" :role="isMobile && mobileOpen ? 'dialog' : undefined" :aria-modal="isMobile && mobileOpen ? true : undefined" aria-label="平台导航">
      <div class="brand"><span class="brand-mark" aria-hidden="true">R</span><span class="nav-label">Runtu<span class="brand-sub">模块化管理平台</span></span></div>
      <button class="mobile-only" @click="close">关闭导航</button>
      <nav aria-label="主导航"><button v-for="entry in entries" :key="entry.id" :aria-label="entry.name" :title="entry.name" :aria-current="page === entry.id ? 'page' : undefined" @click="navigate(entry.id)"><span class="nav-symbol" aria-hidden="true">{{ entry.symbol }}</span><span class="nav-label">{{ entry.name }}</span></button></nav>
      <div class="sidebar-foot"><span class="nav-label">只读管理工作台</span><button class="desktop-only" :aria-expanded="!collapsed" aria-controls="navigation" :aria-label="collapsed ? '展开侧栏' : '折叠侧栏'" @click="collapsed = !collapsed">{{ collapsed ? '»' : '« 折叠侧栏' }}</button></div>
    </aside>
    <div class="workspace" :inert="mobileOpen">
      <header class="toolbar"><div class="toolbar-title"><button ref="menu" class="mobile-only" aria-label="打开导航" :aria-expanded="mobileOpen" aria-controls="navigation" @click="open">☰</button><span>{{ title }}</span></div><div class="toolbar-actions"><span class="connection" role="status">{{ connection }}</span><button @click="$emit('refresh')">刷新数据</button></div></header>
      <main id="main-content" ref="content" tabindex="-1"><div class="page-intro"><p class="platform-name">{{ platform }}</p><h1>{{ title }}</h1></div><slot /></main>
      <footer>Runtu Platform <span>逐步连接所需的管理能力</span></footer>
    </div>
  </div>
</template>

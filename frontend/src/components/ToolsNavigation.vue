<script setup>
import { shallowRef, computed, watch, onMounted, onUnmounted } from 'vue'
import { useResource } from '../composables/useResource.js'
import { readMyModules } from '../api/moduleAccess.js'
import { modulePath } from '../navigation/history.js'
import RouteLink from './RouteLink.vue'
import AppIcon from './AppIcon.vue'
const props = defineProps({ userId: String, path: String, compact: Boolean })
const emit = defineEmits(['navigate', 'expandSidebar'])
const open = shallowRef(false), rows = shallowRef([]), cursor = shallowRef(null)
try { open.value = sessionStorage.getItem('runtu-tools-open') === 'true' } catch { /* Navigation works without storage. */ }
const page = useResource(readMyModules)
const active = computed(() => rows.value.some(row => modulePath(row.module_id) === props.path))
function remember(value) { open.value = value; try { sessionStorage.setItem('runtu-tools-open', String(value)) } catch { /* Optional preference. */ } }
function toggle() { if (props.compact) { emit('expandSidebar'); remember(true) } else remember(!open.value) }
function refresh() { rows.value = []; cursor.value = null; page.load(null) }
function more() { if (!page.pending.value && cursor.value != null) page.load(cursor.value) }
watch(page.data, value => { if (value) { rows.value = [...rows.value, ...value.items]; cursor.value = value.next_after_module; const id = props.path?.split('/')[2]; if (id && cursor.value && id > cursor.value) more() } })
watch(() => props.userId, () => { page.cancel(); rows.value = []; cursor.value = null; page.data.value = null; page.error.value = null; if (props.userId) refresh() }, { immediate: true })
watch(() => [props.path, active.value], () => { if (active.value || props.path === '/tools') remember(true) }, { immediate: true })
onMounted(() => { window.addEventListener('runtu-tools-changed', refresh); window.addEventListener('focus', refresh) })
onUnmounted(() => { page.cancel(); window.removeEventListener('runtu-tools-changed', refresh); window.removeEventListener('focus', refresh) })
</script>
<template>
  <div class="tools-navigation">
    <button class="tools-toggle" :class="{ 'has-active-tool': active }" :aria-expanded="open && !compact" aria-controls="my-tools-navigation" aria-label="我的工具" title="我的工具" @click="toggle"><AppIcon name="module" /><span class="nav-label">我的工具</span><AppIcon class="tools-chevron nav-label" :name="open ? 'left' : 'right'" :size="14" /></button>
    <div v-show="open && !compact" id="my-tools-navigation" class="tools-children">
      <p v-if="!rows.length && page.pending.value" role="status">正在加载工具…</p>
      <div v-else-if="page.error.value" role="alert"><p>{{ page.error.value.message }}</p><button @click="rows.length ? more() : refresh()">重试工具</button></div>
      <p v-else-if="!rows.length" class="tools-empty">暂无已授权工具</p>
      <ul v-if="rows.length"><li v-for="row in rows" :key="row.module_id"><RouteLink :to="modulePath(row.module_id)" :aria-current="path === modulePath(row.module_id) ? 'page' : undefined" :title="row.name" @navigate="emit('navigate')">{{ row.name }}</RouteLink></li></ul>
      <button class="tools-more" v-if="cursor != null" :disabled="page.pending.value" @click="more">{{ page.pending.value ? '加载中…' : '加载更多工具' }}</button>
      <button v-if="!page.pending.value && !page.error.value" class="tools-refresh" @click="refresh">刷新工具</button>
    </div>
  </div>
</template>
<style scoped>
.tools-toggle{display:flex;align-items:center;justify-content:flex-start;gap:13px;width:100%;min-height:46px;padding:12px 14px;border:1px solid transparent;background:transparent;color:#59677a;font-size:14px}.tools-toggle:hover{background:#f2f5f8}.tools-toggle.has-active-tool{color:var(--accent)}.tools-chevron{margin-left:auto;transform:rotate(90deg)}.tools-children{margin:4px 0 8px 18px;padding-left:12px;border-left:1px solid var(--line);max-height:360px;overflow-y:auto;overscroll-behavior:contain}.tools-children p{font-size:12px;color:var(--muted);margin:10px 8px;line-height:1.7}.tools-children button{font-size:12px;min-height:44px;margin:4px 0;max-width:100%}.tools-refresh{border:0;background:transparent;color:var(--muted)}.tools-children a{font-size:13px;overflow-wrap:anywhere}.tools-children a[aria-current=page]::before{display:none}
</style>

<script setup>
import { watch,onMounted,onUnmounted } from 'vue'
import { readMyModules } from '../api/moduleAccess.js'
import { useResource } from '../composables/useResource.js'
import AppIcon from './AppIcon.vue'
import RouteLink from './RouteLink.vue'
import { modulePath } from '../navigation/history.js'
const emit=defineEmits(['count'])
const props=defineProps({userId:String})
async function readAll(signal) {
  const items = []; let cursor = null
  do { const page = await readMyModules(cursor, signal); items.push(...page.items); cursor = page.next_after_module } while (cursor != null)
  return { items, next_after_module: null }
}
const mine=useResource(readAll)
function load(){emit('count',null);mine.load()}
function first(){load()}
watch(()=>props.userId,()=>{mine.cancel();mine.data.value=null;mine.error.value=null;if(props.userId)first()},{immediate:true})
watch(mine.data,value=>emit('count',value ? value.items.length : null))
onMounted(()=>{window.addEventListener('focus',first);window.addEventListener('runtu-tools-changed',first)})
onUnmounted(()=>{mine.cancel();window.removeEventListener('focus',first);window.removeEventListener('runtu-tools-changed',first)})
</script>
<template>
  <section v-if="userId" class="panel my-modules" aria-labelledby="my-modules-title"><div class="section-heading"><h2 id="my-modules-title">我的工具<span v-if="mine.data.value" class="tool-count">{{ mine.data.value.items.length }}</span></h2><button :disabled="mine.pending.value" @click="first">刷新工具</button></div>
    <p v-if="mine.pending.value" role="status">正在确认可用工具…</p>
    <div v-else-if="mine.error.value" role="alert"><p>{{mine.error.value.message}}</p><button @click="load">重试可用工具</button></div>
    <template v-else-if="mine.data.value"><p v-if="!mine.data.value.items.length" class="subtle">还没有分配工具。联系平台所有者获取访问权限，授权后的入口会显示在这里。</p><ul v-else class="tool-grid"><li v-for="row in mine.data.value.items" :key="row.module_id"><RouteLink class="tool-link" :to="modulePath(row.module_id)"><span class="module-avatar"><AppIcon name="module" /></span><span>{{row.name}}</span><AppIcon name="right" :size="16" /></RouteLink></li></ul></template>

  </section>
</template>
<style scoped>
.section-heading{align-items:center;flex-wrap:wrap;gap:12px}h2{margin:0}nav{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}.subtle{margin:0;padding:20px 0;color:var(--muted);font-size:13px}.tool-count{font-size:12px;font-weight:500;display:inline-block;margin-left:10px;background:var(--accent-soft);color:var(--accent);padding:2px 8px;border-radius:12px}
</style>

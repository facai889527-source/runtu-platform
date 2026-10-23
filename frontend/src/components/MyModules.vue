<script setup>
import { ref,watch,onUnmounted } from 'vue'
import { readMyModules } from '../api/moduleAccess.js'
import { useResource } from '../composables/useResource.js'
import AppIcon from './AppIcon.vue'
import RouteLink from './RouteLink.vue'
import { modulePath } from '../navigation/history.js'
const props=defineProps({userId:String})
const mine=useResource(readMyModules),after=ref(null),previous=ref([])
function load(){mine.load(after.value)}
function first(){after.value=null;previous.value=[];load()}
function next(){const cursor=mine.data.value?.next_after_module;if(cursor!=null){previous.value.push(after.value);after.value=cursor;load()}}
function back(){if(previous.value.length){after.value=previous.value.pop();load()}}
watch(()=>props.userId,()=>{mine.cancel();mine.data.value=null;mine.error.value=null;if(props.userId)first()},{immediate:true})
onUnmounted(mine.cancel)
</script>
<template>
  <section v-if="userId" class="panel my-modules" aria-labelledby="my-modules-title"><div class="section-heading"><h2 id="my-modules-title">可用工具</h2><button :disabled="mine.pending.value" @click="first">刷新工具</button></div>
    <p v-if="mine.pending.value" role="status">正在确认可用工具…</p>
    <div v-else-if="mine.error.value" role="alert"><p>{{mine.error.value.message}}</p><button @click="load">重试可用工具</button></div>
    <template v-else-if="mine.data.value"><p v-if="!mine.data.value.items.length" class="subtle">暂无可用工具。获得工具授权后，将在这里显示；如需访问，请联系平台所有者。</p><ul v-else class="tool-grid"><li v-for="row in mine.data.value.items" :key="row.module_id"><RouteLink class="tool-link" :to="modulePath(row.module_id)"><span class="module-avatar"><AppIcon name="module" /></span><span>{{row.name}}</span><AppIcon name="right" :size="16" /></RouteLink></li></ul></template>
    <nav v-if="previous.length || mine.data.value?.next_after_module != null" aria-label="我的工具分页"><button :disabled="mine.pending.value||!previous.length" @click="back">上一页工具</button><button :disabled="mine.pending.value||mine.data.value?.next_after_module==null" @click="next">下一页工具</button></nav>
  </section>
</template>
<style scoped>
.section-heading{align-items:center;flex-wrap:wrap;gap:12px}h2{margin:0}nav{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}.subtle{margin:0;padding:28px 12px;border:1px dashed var(--line-strong);border-radius:var(--radius-sm);text-align:center}
</style>

<script setup>
import { ref,watch,onUnmounted } from 'vue'
import { readMyModules } from '../api/moduleAccess.js'
import { useResource } from '../composables/useResource.js'
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
  <section v-if="userId" class="panel my-modules" aria-labelledby="my-modules-title"><div class="section-heading"><h2 id="my-modules-title">我的业务模块</h2><button :disabled="mine.pending.value" @click="first">刷新可用模块</button></div>
    <p v-if="mine.pending.value" role="status">正在确认可用模块…</p>
    <div v-else-if="mine.error.value" role="alert"><p>{{mine.error.value.message}}</p><button @click="load">重试可用模块</button></div>
    <template v-else-if="mine.data.value"><p v-if="!mine.data.value.items.length" class="subtle">暂无已授权且启用的业务模块。公开演示模块仍可在目录查看。</p><ul v-else><li v-for="row in mine.data.value.items" :key="row.module_id"><RouteLink :to="modulePath(row.module_id)">{{row.name}}</RouteLink></li></ul></template>
    <nav aria-label="我的模块分页"><button :disabled="mine.pending.value||!previous.length" @click="back">上一页模块</button><button :disabled="mine.pending.value||mine.data.value?.next_after_module==null" @click="next">下一页模块</button></nav>
  </section>
</template>
<style scoped>
.my-modules{padding:24px;margin-top:20px}.section-heading{align-items:center;flex-wrap:wrap;gap:12px}h2{margin:0}nav{display:flex;gap:10px;justify-content:flex-end;margin-top:16px}button{min-height:44px}li{margin:12px 0}@media(max-width:760px){.my-modules{padding:20px}}
</style>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { readPending, approve } from '../api/registration.js'
const page = ref(null), after = ref(null), previous = ref([]), busy = ref(false), error = ref('')
let controller, timer, live = true
async function load() {
  controller?.abort(); clearTimeout(timer); controller = new AbortController()
  const own = controller
  busy.value = true; error.value = ''; page.value = null; timer = setTimeout(() => own.abort(), 10000)
  try { const value = await readPending(after.value, own.signal); if (live && controller === own) page.value = value }
  catch (cause) { if (live && controller === own) error.value = cause.name === 'AbortError' ? '查询未完成，请重试。' : cause.message }
  finally { if (controller === own) { clearTimeout(timer); if (live) busy.value = false } }
}
function first() { after.value = null; previous.value = []; load() }
function next() { previous.value.push(after.value); after.value = page.value.next_after_username; load() }
function back() { after.value = previous.value.pop(); load() }
async function accept(item) {
  if (busy.value || !window.confirm(`确认已独立核实 ${item.username} 的身份，并批准为只读成员？`)) return
  busy.value = true; error.value = ''; controller = new AbortController(); timer = setTimeout(() => controller.abort(), 10000)
  let saved = false
  try { await approve(item.id, controller.signal); saved = true }
  catch (cause) { if (live) { error.value = cause.name === 'AbortError' ? '批准结果未确认，请先刷新列表。' : cause.message; busy.value = false } }
  finally { clearTimeout(timer); if (live) busy.value = false }
  if (saved && live) first()
}
onMounted(load)
onUnmounted(() => { live = false; controller?.abort(); clearTimeout(timer) })
</script>
<template>
  <section class="panel approvals" aria-labelledby="approvals-title"><div class="section-heading"><h2 id="approvals-title">待审核注册</h2><button :disabled="busy" @click="first">刷新申请</button></div>
    <p class="subtle">批准前请通过独立渠道核实身份。批准后仍需另行授予业务模块。</p>
    <p v-if="busy" role="status">正在处理申请…</p><p v-if="error" role="alert">{{ error }}</p>
    <template v-if="page && !busy"><p v-if="!page.items.length">此页没有待审核申请。</p><ul v-else><li v-for="item in page.items" :key="item.id"><span>{{ item.username }} <small>待审核 · 无法登录</small></span><button @click="accept(item)">批准为只读成员</button></li></ul></template>
    <nav aria-label="注册申请分页"><button :disabled="busy || !previous.length" @click="back">上一页</button><button :disabled="busy || !page?.next_after_username" @click="next">下一页</button></nav>
  </section>
</template>
<style scoped>
.approvals { padding: 24px; min-width: 0; } .section-heading, li { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; } ul { list-style: none; padding: 0; } li { padding: 16px 0; border-top: 1px solid var(--line); overflow-wrap: anywhere; } small { display: block; color: var(--muted); margin-top: 6px; } nav { display: flex; justify-content: flex-end; gap: 12px; } button { min-height: 44px; } [role=alert] { color: var(--danger); }
</style>

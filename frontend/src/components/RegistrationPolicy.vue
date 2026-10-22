<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { readPolicy, savePolicy } from '../api/registration.js'
const current = ref(null), enabled = ref(false), approval = ref(true), busy = ref(false), error = ref(''), message = ref('')
let controller, timer, live = true
async function operation(save = false) {
  if (busy.value) return
  if (save && enabled.value && !window.confirm('确认开放公开注册？请先核实访问范围和审核安排。')) return
  busy.value = true; error.value = ''; message.value = ''
  controller = new AbortController(); timer = setTimeout(() => controller.abort(), 10000)
  try {
    const value = save ? await savePolicy({ enabled: enabled.value, approval_required: approval.value, expected_revision: current.value.revision }, controller.signal) : await readPolicy(controller.signal)
    if (live) { current.value = value; enabled.value = value.enabled; approval.value = value.approval_required; if (save) message.value = '注册策略已保存。' }
  } catch (cause) { if (live) error.value = cause.name === 'AbortError' ? '结果未确认，请刷新策略后重试。' : cause.message }
  finally { clearTimeout(timer); if (live) busy.value = false }
}
onMounted(() => operation())
onUnmounted(() => { live = false; controller?.abort(); clearTimeout(timer) })
</script>
<template>
  <section class="panel registration-policy" aria-labelledby="registration-policy-title">
    <div class="section-heading"><h2 id="registration-policy-title">注册策略</h2><button :disabled="busy" @click="operation()">刷新策略</button></div>
    <p class="subtle">新账户仅为只读成员，默认没有业务模块授权。关闭审核仅影响之后的注册。</p>
    <p v-if="busy" role="status">正在处理注册策略…</p>
    <form v-if="current" @submit.prevent="operation(true)"><fieldset :disabled="busy"><legend>账户申请规则</legend>
      <label><input v-model="enabled" type="checkbox" />开放公开注册</label>
      <label><input v-model="approval" type="checkbox" />新账户需要所有者审核</label>
      <p v-if="enabled && !approval" class="warning">未要求审核：后续新账户可直接登录，但仍没有业务模块授权。</p>
      <button type="submit">保存注册策略</button>
    </fieldset></form>
    <p v-if="error" role="alert">{{ error }}</p><p v-if="message" role="status">{{ message }}</p>
  </section>
</template>
<style scoped>
.registration-policy { padding: 24px; } .section-heading { flex-wrap: wrap; gap: 12px; } fieldset { border: 0; padding: 0; margin: 18px 0 0; display: grid; gap: 16px; } label { display: flex; align-items: center; gap: 10px; min-height: 44px; } input { width: 18px; height: 18px; } button { min-height: 44px; } .warning { color: #805218; } [role=alert] { color: var(--danger); }
</style>

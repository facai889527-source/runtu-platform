<script setup>
import PolicySwitch from './PolicySwitch.vue'
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { readPolicy, savePolicy } from '../api/registration.js'
const current = ref(null), enabled = ref(false), approval = ref(true), busy = ref(false), error = ref(''), message = ref('')
const dirty = computed(() => current.value && (enabled.value !== current.value.enabled || approval.value !== current.value.approval_required))
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
    <p class="subtle">新账户仅为只读成员，默认没有业务工具授权。关闭审核仅影响之后的注册。</p>
    <p v-if="busy" role="status">正在处理注册策略…</p>
    <form v-if="current" @submit.prevent="operation(true)"><fieldset :disabled="busy"><legend>账户申请规则</legend>
      <PolicySwitch v-model="enabled" label="开放公开注册" description="允许访客提交账户申请。关闭后不再接受新申请。" />
      <PolicySwitch v-model="approval" label="新账户需要所有者审核" description="审核通过后才能登录；工具访问仍需单独授权。" />
      <p v-if="enabled && !approval" class="warning">未要求审核：后续新账户可直接登录，但仍没有业务工具授权。</p>
      <div class="policy-actions"><span class="subtle">{{ dirty ? '有未保存的更改' : '当前策略已同步' }}</span><button type="submit" :disabled="!dirty">保存注册策略</button></div>
    </fieldset></form>
    <p v-if="error" role="alert">{{ error }}</p><p v-if="message" role="status">{{ message }}</p>
  </section>
</template>
<style scoped>
.registration-policy { padding: 24px; } .section-heading { flex-wrap: wrap; gap: 12px; } fieldset { border: 0; padding: 0; margin: 18px 0 0; display: grid; gap: 0; } .policy-actions { padding-top:16px; display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px } label { display: flex; align-items: center; gap: 10px; min-height: 44px; } input { width: 18px; height: 18px; } button { min-height: 44px; } .warning { color: #805218; } [role=alert] { color: var(--danger); }
</style>

<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
import { saveModule } from '../api/moduleManagement.js'
import RouteLink from './RouteLink.vue'
const props = defineProps({ detail: { type: Object, required: true }, access: { type: Object, required: true } })
const emit = defineEmits(['saved', 'reload'])
const enabled = ref(true), visible = ref(true), interval = ref('')
const busy = ref(false), error = ref(''), success = ref('')
const canManage = computed(() => !props.access.pending.value && !props.access.error.value && props.access.data.value?.permissions.includes('module.manage'))
let controller, timer
watch(() => props.detail, (value) => {
  enabled.value = value.status === 'enabled'; visible.value = value.public_config.show_in_navigation
  interval.value = value.public_config.refresh_interval_seconds ?? ''
}, { immediate: true })
async function submit() {
  if (busy.value || !canManage.value) return
  if (!enabled.value && props.detail.status === 'enabled' && !window.confirm('禁用后此模块的业务接口将不可用。确定禁用并保存？')) return
  busy.value = true; error.value = ''; success.value = ''; controller = new AbortController()
  timer = setTimeout(() => controller.abort(), 10000)
  try {
    const result = await saveModule(props.detail.id, { enabled: enabled.value,
      expected_revision: props.detail.revision,
      public_config: { show_in_navigation: visible.value, refresh_interval_seconds: interval.value === '' ? null : Number(interval.value) } }, controller.signal)
    emit('saved', result); success.value = '已保存，模块状态与配置已更新。'
  } catch (failure) {
    error.value = failure.name === 'AbortError' ? '保存结果未确认，请重新加载模块后检查。' : failure.message || '保存失败，请重试。'
    if ([401, 403].includes(failure.status)) props.access.load()
  } finally { clearTimeout(timer); busy.value = false }
}
onUnmounted(() => { clearTimeout(timer); controller?.abort() })
</script>

<template>
  <section class="panel module-editor" aria-labelledby="module-management-title">
    <div class="section-heading"><h2 id="module-management-title">模块管理</h2><span v-if="detail.required" class="readonly-label">必需模块</span></div>
    <p v-if="access.pending.value" role="status">正在确认管理权限…</p>
    <div v-else-if="access.error.value"><p>管理权限暂无法确认。</p><button @click="access.load()">重试权限查询</button></div>
    <template v-else-if="!canManage"><p v-if="access.data.value">当前角色可查看模块，没有模块管理权限。</p><RouteLink v-else to="/login">登录后管理模块</RouteLink></template>
    <form v-else class="module-editor-form" @submit.prevent="submit" :aria-busy="busy">
      <fieldset :disabled="busy"><legend class="sr-only">模块状态与公开配置</legend>
        <label class="check-field"><input type="checkbox" v-model="enabled" :disabled="detail.required" />启用本模块</label>
        <p v-if="detail.required" class="subtle">此模块为平台必需模块，不能禁用。</p>
        <label class="check-field"><input type="checkbox" v-model="visible" />导航展示偏好</label>
        <label class="interval-field">刷新间隔偏好（秒）<input v-model="interval" type="number" min="1" max="86400" step="1" placeholder="未设置" /></label>
        <p class="subtle">仅保存公开偏好；不会据此自动刷新页面或隐藏目录条目。</p>
      </fieldset>
      <div class="editor-actions"><button type="submit" :disabled="busy">{{ busy ? '保存中…' : '保存更改' }}</button><button type="button" :disabled="busy" @click="$emit('reload')">重新加载</button></div>
    </form>
    <p v-if="error" class="error" role="alert">{{ error }}</p><p v-if="success" class="save-success" role="status">{{ success }}</p>
  </section>
</template>

<style scoped>
.module-editor-form fieldset { border: 0; padding: 0; margin: 0; display: grid; gap: 16px; }
.check-field { display: flex; gap: 10px; align-items: center; font-size: 14px; }
.check-field input { min-height: 20px; width: 20px; accent-color: var(--accent); }
.interval-field { display: grid; gap: 8px; max-width: 320px; font-size: 14px; }
.editor-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 20px; }
.editor-actions button[type=submit] { background: var(--accent); color: white; border-color: var(--accent); }
.save-success { color: var(--accent); margin: 16px 0 0; }
.module-editor .error { margin: 16px 0 0; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
</style>

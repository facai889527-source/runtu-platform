<script setup>
import { shallowRef, onUnmounted } from 'vue'
import { readModule } from '../api/client.js'
import { saveModule } from '../api/moduleManagement.js'
const props = defineProps({ item: Object })
const emit = defineEmits(['changed'])
const busy = shallowRef(false), error = shallowRef('')
let controller, timer
async function toggle() {
  if (busy.value) return
  const enabled = props.item.status !== 'enabled'
  if (!enabled && !window.confirm('禁用后此工具的业务接口将不可用。确定禁用？')) return
  busy.value = true; error.value = ''; controller = new AbortController(); timer = setTimeout(() => controller.abort(), 10000)
  try {
    const detail = await readModule(props.item.id, controller.signal)
    if (detail.status !== props.item.status) throw new Error('工具状态已变化，请刷新后确认。')
    if (!enabled && detail.required) throw new Error('此工具为平台必需工具，不能禁用。')
    await saveModule(detail.id, { enabled, expected_revision: detail.revision, public_config: detail.public_config }, controller.signal)
    emit('changed'); window.dispatchEvent(new Event('runtu-tools-changed'))
  } catch (cause) { error.value = cause.name === 'AbortError' ? '结果未确认，请刷新后检查。' : cause.message }
  finally { clearTimeout(timer); busy.value = false }
}
onUnmounted(() => { controller?.abort(); clearTimeout(timer) })
</script>
<template><div class="tool-admin-actions"><button :disabled="busy" :aria-label="`${item.status === 'enabled' ? '禁用' : '启用'}${item.name}`" @click="toggle">{{ busy ? '处理中…' : item.status === 'enabled' ? '禁用工具' : '启用工具' }}</button><p v-if="error" role="alert">{{ error }}</p></div></template>
<style scoped>.tool-admin-actions{position:relative;z-index:1;margin-top:16px}.tool-admin-actions button{font-size:12px;min-height:44px}.tool-admin-actions p{font-size:12px;color:var(--danger);margin:10px 0 0}</style>

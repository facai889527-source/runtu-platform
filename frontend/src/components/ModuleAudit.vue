<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
import { readModuleAudit } from '../api/moduleAudit.js'
import { useResource } from '../composables/useResource.js'

const props = defineProps({ moduleId: { type: String, required: true }, access: Object, revision: Number })
const records = useResource(readModuleAudit)
const allowed = computed(() => Boolean(props.access?.data.value?.permissions.includes('audit.read')))
const cursor = ref(null), previous = ref([])
function load() { records.load(props.moduleId, cursor.value) }
function first() { cursor.value = null; previous.value = []; load() }
function older() {
  if (records.data.value?.next_before_revision == null) return
  previous.value.push(cursor.value)
  cursor.value = records.data.value.next_before_revision
  load()
}
function newer() { if (previous.value.length) { cursor.value = previous.value.pop(); load() } }
watch(() => [props.moduleId, allowed.value, props.revision], () => {
  records.cancel(); records.data.value = null; records.error.value = null
  cursor.value = null; previous.value = []
  if (allowed.value) load()
}, { immediate: true })
onUnmounted(records.cancel)
function timeLabel(value) { return new Date(value).toLocaleString('zh-CN', { hour12: false }) }
</script>

<template>
  <section class="panel module-audit" aria-labelledby="audit-title">
    <div class="section-heading"><div><h2 id="audit-title">操作记录</h2><p class="subtle">按变更版本从新到旧排列</p></div><button v-if="allowed" type="button" :disabled="records.pending.value" @click="first">刷新记录</button></div>
    <p v-if="access?.pending.value" role="status">正在确认查看权限…</p>
    <div v-else-if="access?.error.value" role="status">查看权限暂无法确认。<button type="button" @click="access.load()">重试权限查询</button></div>
    <p v-else-if="!allowed" class="subtle">当前身份没有查看操作记录的权限。</p>
    <template v-else>
      <p v-if="records.pending.value" role="status">正在加载操作记录…</p>
      <div v-else-if="records.error.value" role="alert"><p>{{ records.error.value.message }}</p><button type="button" @click="load">重试加载</button></div>
      <template v-else-if="records.data.value">
        <p v-if="!records.data.value.items.length" class="subtle">{{ cursor === null ? '此模块暂无操作记录。保存模块变更后会在这里显示。' : '此页没有更早的记录，请返回较新记录或刷新。' }}</p>
        <ol v-else class="audit-list">
          <li v-for="item in records.data.value.items" :key="item.revision">
            <div class="audit-entry-heading"><strong>更新模块设置</strong><span class="audit-revision">版本 {{ item.revision }}</span></div>
            <dl><div><dt>操作者标识</dt><dd>{{ item.actor_id }}</dd></div><div><dt>模块</dt><dd>{{ item.module_id }}</dd></div><div><dt>时间（本地）</dt><dd><time :datetime="item.created_at">{{ timeLabel(item.created_at) }}</time></dd></div></dl>
          </li>
        </ol>
      </template>
      <nav class="audit-pagination" aria-label="操作记录分页">
        <button type="button" :disabled="records.pending.value || !previous.length" @click="newer">较新记录</button>
        <button type="button" :disabled="records.pending.value || records.data.value?.next_before_revision == null" @click="older">更早记录</button>
      </nav>
    </template>
  </section>
</template>

<style scoped>
.module-audit { margin-top: 20px; padding: 24px; }
.module-audit h2 { margin: 0; }
.module-audit .section-heading { align-items: center; gap: 16px; }
.module-audit .section-heading p { margin: 6px 0 0; }
.module-audit button { min-height: 44px; }
.audit-list { list-style: none; padding: 0; margin: 0; }
.audit-list li { border-top: 1px solid var(--line); padding: 18px 0; }
.audit-entry-heading { display: flex; justify-content: space-between; gap: 12px; }
.audit-revision { color: var(--muted); white-space: nowrap; }
.audit-list dl { display: grid; grid-template-columns: 2fr 1fr 1.5fr; gap: 12px; margin: 12px 0 0; font-size: 13px; }
.audit-list dt { color: var(--muted); margin-bottom: 4px; }
.audit-list dd { margin: 0; overflow-wrap: anywhere; }
.audit-pagination { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }
@media (max-width: 760px) { .module-audit { padding: 20px; } .audit-list dl { grid-template-columns: 1fr; } .module-audit .section-heading { flex-wrap: wrap; } }
</style>

<script setup>
import { watch, onMounted, onUnmounted } from 'vue'
import { readLoginActivity } from '../api/auth.js'
import { useResource } from '../composables/useResource.js'
const props = defineProps({ userId: String })
const activity = useResource(readLoginActivity)
watch(() => props.userId, () => { activity.cancel(); activity.data.value = null; if (props.userId) activity.load() }, { immediate: true })
function refresh() { activity.load() }
onMounted(() => window.addEventListener('focus', refresh))
onUnmounted(() => { activity.cancel(); window.removeEventListener('focus', refresh) })
function localTime(value) { return new Date(value).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }) }
</script>
<template><section class="login-activity" aria-labelledby="previous-login-title"><div class="activity-heading"><h2 id="previous-login-title">上次成功登录</h2><span>本地时间</span></div><p v-if="activity.pending.value" role="status">正在读取记录…</p><div v-else-if="activity.error.value" class="activity-error" role="status"><p>登录记录暂不可用</p><button @click="activity.load()">重试</button></div><dl v-else-if="activity.data.value"><div><dt>登录时间</dt><dd><time v-if="activity.data.value.previous_login" :datetime="activity.data.value.previous_login.at">{{ localTime(activity.data.value.previous_login.at) }}</time><span v-else>暂无记录</span></dd></div><div><dt>IP 地址</dt><dd>{{ activity.data.value.previous_login ? activity.data.value.previous_login.ip || '未记录' : '暂无记录' }}</dd></div></dl><p class="privacy-note">仅展示当前账户的上一次成功登录；转发来源不明时不记录 IP。</p></section></template>
<style scoped>
.login-activity{padding:24px;background:#fff;border:1px solid var(--line);border-radius:var(--radius)}.activity-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.activity-heading h2{font-size:14px}.activity-heading span,dt{font-size:12px;color:var(--muted)}dl{display:grid;grid-template-columns:1.6fr 1fr;gap:20px;margin:24px 0 16px}dd{margin:9px 0 0;font-size:16px;font-weight:550;overflow-wrap:anywhere}.privacy-note{font-size:11px;color:var(--muted);margin:18px 0 0;line-height:1.7}.activity-error{display:flex;align-items:center;gap:16px}.activity-error p{margin:0}.activity-error button{font-size:12px}@media(max-width:760px){.login-activity{padding:20px}dl{grid-template-columns:1fr;gap:18px}dd{font-size:15px}}
</style>

<script setup>
import { computed, shallowRef } from 'vue'
import ResourceState from '../components/ResourceState.vue'
import HomeLoginActivity from '../components/HomeLoginActivity.vue'
import MyModules from '../components/MyModules.vue'
import RouteLink from '../components/RouteLink.vue'
import AppIcon from '../components/AppIcon.vue'
import { databaseLabels, moduleCounts } from '../utils/modules.js'
import { modulePath } from '../navigation/history.js'
const props = defineProps({ health: Object, modules: Object, userId: String, showDiagnostics: Boolean, user: Object, access: Object })
const authorizedCount = shallowRef(null)
const role = computed(() => ({ owner: '所有者', admin: '管理员', viewer: '只读成员' }[props.access?.data.value?.role] || '待确认'))
const counts = computed(() => props.modules.data.value ? moduleCounts(props.modules.data.value) : null)
const publicTools = computed(() => props.modules.data.value?.filter(item => item.access_mode !== 'assigned' && item.status === 'enabled') || [])
</script>
<template>
  <section class="home-welcome" aria-labelledby="welcome-title"><div><p class="home-kicker">欢迎回到润土平台</p><h2 id="welcome-title" :class="{ 'long-user': user?.username?.length > 24 }"><span class="welcome-name" :title="user?.username">{{ user?.username || '当前用户' }}</span><span>{{ user?.username?.length > 24 ? '您好！' : '，您好！' }}</span></h2><div class="account-facts"><span>{{ role }}</span><span class="account-active"><i aria-hidden="true" />账户已启用</span></div></div><div class="authorized-total"><strong>{{ authorizedCount == null ? '—' : authorizedCount }}</strong><span>已授权工具</span></div></section>
  <div class="home-overview"><HomeLoginActivity :user-id="userId" /><section class="home-guide"><AppIcon name="module" :size="24" /><h2>从工具开始</h2><p>展开左侧“我的工具”即可进入已授权工具，也可以使用下方入口。</p></section></div>
  <MyModules :user-id="userId" @count="authorizedCount = $event" />
  <section v-if="publicTools.length" class="public-tools" aria-labelledby="public-tools-title">
    <div class="section-heading"><div><h2 id="public-tools-title">公开工具</h2><p class="section-description">用于了解平台的公开演示，不属于个人授权工具。</p></div></div>
    <ul class="tool-grid"><li v-for="item in publicTools" :key="item.id"><RouteLink class="tool-link overview-name" :to="modulePath(item.id)"><span class="module-avatar"><AppIcon name="module" /></span><span><strong>{{ item.name }}</strong><small>{{ item.description }}</small></span><AppIcon name="right" :size="16" /></RouteLink></li></ul>
  </section>
  <details v-if="showDiagnostics" class="panel system-status"><summary>平台运行状态<span class="subtle">管理员诊断</span></summary>
    <ResourceState :pending="health.pending.value" :error="health.error.value" @retry="health.load()"><dl v-if="health.data.value" class="diagnostic-grid"><div><dt>后端服务</dt><dd>{{ health.data.value.status === 'ok' ? '运行正常' : '服务降级' }}</dd></div><div><dt>数据库</dt><dd>{{ databaseLabels[health.data.value.database] }}</dd></div><div v-if="counts"><dt>工具清单</dt><dd>{{ counts.enabled }} 已启用 / {{ counts.total }} 已注册</dd></div></dl></ResourceState>
  </details>
</template>

<style scoped>
.home-welcome{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:14px 0 30px}.home-kicker{font-size:13px;color:var(--muted);margin:0 0 10px}#welcome-title{font-size:30px;line-height:1.4;letter-spacing:-.04em;font-weight:650;overflow-wrap:anywhere}.long-user .welcome-name{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.account-facts{display:flex;gap:14px;flex-wrap:wrap;margin-top:16px;color:var(--muted);font-size:12px}.account-active{display:inline-flex;align-items:center;gap:6px}.account-active i{width:6px;height:6px;background:var(--accent);border-radius:50%}.authorized-total{display:grid;gap:6px;border-left:1px solid var(--line-strong);padding:8px 32px;flex-shrink:0}.authorized-total strong{font-size:36px;line-height:1.2;font-weight:600;color:var(--accent);font-variant-numeric:tabular-nums}.authorized-total span{font-size:12px;color:var(--muted)}.home-overview{display:grid;grid-template-columns:1.6fr 1fr;gap:20px;margin-bottom:20px}.home-guide{padding:24px;border-radius:var(--radius);background:#eaf2ef;border:1px solid #d7e7e0}.home-guide>.app-icon{color:var(--accent);margin-bottom:20px}.home-guide h2{font-size:16px;margin-bottom:8px}.home-guide p{font-size:13px;color:#4c685e;margin:0;max-width:36em}.public-tools{margin:26px 0}.public-tools .section-heading{margin-bottom:14px}.public-tools :deep(.tool-link){background:#fff;min-height:88px}.public-tools h2{font-size:14px}.system-status{margin-top:24px}.home-welcome>div:first-child{min-width:0}@media(max-width:760px){.home-welcome{align-items:flex-start;padding:8px 0 24px;gap:12px}#welcome-title{font-size:24px}.authorized-total{padding:8px 0 8px 16px}.authorized-total strong{font-size:30px}.home-overview{grid-template-columns:1fr}.home-guide{display:none}.account-facts{gap:10px}.public-tools{margin:24px 0}}
</style>

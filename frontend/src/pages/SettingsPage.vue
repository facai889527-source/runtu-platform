<script setup>
import { computed } from 'vue'
import RegistrationPolicy from '../components/RegistrationPolicy.vue'
import RegistrationApprovals from '../components/RegistrationApprovals.vue'
import RouteLink from '../components/RouteLink.vue'
import AppIcon from '../components/AppIcon.vue'
const props = defineProps({ access: Object })
const canManageAccounts = computed(() => Boolean(props.access?.data.value?.role === 'owner' && props.access.data.value.permissions.includes('users.manage')))
const canManageModules = computed(() => Boolean(props.access?.data.value?.permissions.includes('module.manage')))
</script>
<template>
  <div class="settings-page">
    <p v-if="access?.pending.value" role="status">正在确认设置权限…</p>
    <p v-else-if="access?.error.value" role="alert">设置权限暂无法确认。<button @click="access.load()">重试权限查询</button></p>
    <template v-else>
      <section v-if="canManageModules" class="panel module-settings" aria-labelledby="module-settings-title">
        <div class="section-heading"><div><h2 id="module-settings-title">模块与工具</h2><p class="section-description">维护已接入模块的启用状态和公开配置。</p></div></div>
        <RouteLink class="settings-module-link" to="/modules"><span class="module-avatar"><AppIcon name="module" /></span><span><strong>模块管理</strong><small>查看模块目录与管理详情</small></span><AppIcon name="right" :size="18" /></RouteLink>
      </section>
      <template v-if="canManageAccounts"><RegistrationPolicy /><RegistrationApprovals /></template>
      <section v-if="!canManageModules && !canManageAccounts" class="panel settings"><p>当前身份没有全局设置权限。注册策略和账户审核仅向所有者开放。</p></section>
    </template>
  </div>
</template>
<style scoped>
.settings-page { display: grid; gap: 20px; }
.settings-page :deep(> .panel) { margin-bottom: 0; }
.settings-module-link { display:flex;align-items:center;gap:16px;max-width:560px;min-height:92px;padding:16px;border:1px solid var(--line);border-radius:var(--radius-sm);text-decoration:none;color:var(--ink); }
.settings-module-link:hover { border-color:var(--accent);background:var(--accent-soft); }
.settings-module-link>span:nth-child(2) { flex:1;min-width:0; }
.settings-module-link strong { display:block;font-size:14px;font-weight:600; }
.settings-module-link small { display:block;margin-top:6px;font-size:12px;line-height:1.6; }
</style>

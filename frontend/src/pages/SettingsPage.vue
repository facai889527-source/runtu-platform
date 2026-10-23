<script setup>
import { computed } from 'vue'
import RegistrationPolicy from '../components/RegistrationPolicy.vue'
import RegistrationApprovals from '../components/RegistrationApprovals.vue'
import ModulesPage from './ModulesPage.vue'
const props = defineProps({ access: Object, modules: Object })
defineEmits(['changed'])
const canManageAccounts = computed(() => Boolean(props.access?.data.value?.role === 'owner' && props.access.data.value.permissions.includes('users.manage')))
const canManageModules = computed(() => Boolean(props.access?.data.value?.permissions.includes('module.manage')))
</script>
<template>
  <div class="settings-page">
    <p v-if="access?.pending.value" role="status">正在确认设置权限…</p>
    <p v-else-if="access?.error.value" role="alert">设置权限暂无法确认。<button @click="access.load()">重试权限查询</button></p>
    <template v-else>
      <ModulesPage v-if="canManageModules" :modules="modules" :access="access" @changed="$emit('changed')" />
      <template v-if="canManageAccounts"><RegistrationPolicy /><RegistrationApprovals /></template>
      <section v-if="!canManageModules && !canManageAccounts" class="panel settings"><p>当前身份没有全局设置权限。注册策略和账户审核仅向所有者开放。</p></section>
    </template>
  </div>
</template>
<style scoped>
.settings-page { display: grid; gap: 20px; }
.settings-page :deep(> .panel) { margin-bottom: 0; }
</style>

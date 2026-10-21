<script setup>
import { computed } from 'vue'
import RegistrationPolicy from '../components/RegistrationPolicy.vue'
import RegistrationApprovals from '../components/RegistrationApprovals.vue'
const props = defineProps({ access: Object })
const allowed = computed(() => Boolean(props.access?.data.value?.permissions.includes('users.manage')))
</script>
<template><div class="settings-page"><p v-if="access?.pending.value" role="status">正在确认设置权限…</p><p v-else-if="access?.error.value" role="alert">设置权限暂无法确认。<button @click="access.load()">重试权限查询</button></p><template v-else-if="allowed"><RegistrationPolicy /><RegistrationApprovals /></template><section v-else class="panel settings"><h2>平台设置</h2><p>注册策略和账户审核仅向所有者开放。</p></section></div></template>
<style scoped>.settings-page { display: grid; gap: 20px; }</style>

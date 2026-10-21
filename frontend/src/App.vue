<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import AppLayout from './components/AppLayout.vue'
import DashboardPage from './pages/DashboardPage.vue'
import ModulesPage from './pages/ModulesPage.vue'
import SettingsPage from './pages/SettingsPage.vue'
import { useResource } from './composables/useResource.js'
import { readHealth, readModules } from './api/client.js'
const page = ref('dashboard')
const health = useResource(readHealth), modules = useResource(readModules)
const connection = computed(() => health.pending.value ? '正在连接' : health.error.value ? '连接失败' : health.data.value?.status === 'degraded' ? '后端已连接 · 服务降级' : '后端已连接')
function refresh() { health.load(); modules.load() }
onMounted(refresh)
onUnmounted(() => { health.cancel(); modules.cancel() })
</script>
<template>
  <AppLayout :page="page" :connection="connection" :platform="health.data.value?.platform || 'Runtu Platform'" @navigate="page = $event" @refresh="refresh">
    <DashboardPage v-if="page === 'dashboard'" :health="health" :modules="modules" @navigate="page = 'modules'" />
    <ModulesPage v-else-if="page === 'modules'" :modules="modules" />
    <SettingsPage v-else />
  </AppLayout>
</template>

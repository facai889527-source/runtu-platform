<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import AppLayout from './components/AppLayout.vue'
import DashboardPage from './pages/DashboardPage.vue'
import ModulesPage from './pages/ModulesPage.vue'
import SettingsPage from './pages/SettingsPage.vue'
import NotFoundPage from './pages/NotFoundPage.vue'
import { provideNavigation } from './navigation/context.js'
import { useResource } from './composables/useResource.js'
import { readHealth, readModules } from './api/client.js'
const { route } = provideNavigation()
const health = useResource(readHealth), modules = useResource(readModules)
const connection = computed(() => health.pending.value ? '正在连接' : health.error.value ? '连接失败' : health.data.value?.status === 'degraded' ? '后端已连接 · 服务降级' : '后端已连接')
function refresh() { health.load(); modules.load() }
onMounted(refresh)
onUnmounted(() => { health.cancel(); modules.cancel() })
</script>
<template>
  <AppLayout :page="route.page" :title="route.title" :path="route.path" :connection="connection" :platform="health.data.value?.platform || 'Runtu Platform'" @refresh="refresh">
    <DashboardPage v-if="route.page === 'dashboard'" :health="health" :modules="modules" />
    <ModulesPage v-else-if="route.page === 'modules'" :modules="modules" :module-id="route.moduleId" />
    <SettingsPage v-else-if="route.page === 'settings'" />
    <NotFoundPage v-else />
  </AppLayout>
</template>

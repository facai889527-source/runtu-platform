<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import AppLayout from './components/AppLayout.vue'
import AuthLayout from './components/AuthLayout.vue'
import UserMenu from './components/UserMenu.vue'
import DashboardPage from './pages/DashboardPage.vue'
import ModulesPage from './pages/ModulesPage.vue'
import SettingsPage from './pages/SettingsPage.vue'
import NotFoundPage from './pages/NotFoundPage.vue'
import LoginPage from './pages/LoginPage.vue'
import { readIdentity } from './api/auth.js'
import { provideNavigation } from './navigation/context.js'
import { useResource } from './composables/useResource.js'
import { readHealth, readModules } from './api/client.js'
const { route, navigate } = provideNavigation()
const health = useResource(readHealth), modules = useResource(readModules)
const identity = useResource(readIdentity)
const identityChecked = ref(false)
async function loadIdentity() { await identity.load(); identityChecked.value = true }
watch(() => route.value.page, (page) => { if (page === 'login') loadIdentity() })
watch(() => [route.value.page, identity.data.value?.authenticated], ([page, authenticated]) => {
  if (page === 'login' && authenticated) navigate('/')
})
async function signedOut() { await loadIdentity(); navigate('/login') }
function refresh() { health.load(); modules.load(); loadIdentity() }
function refreshIdentity() { if (document.visibilityState === 'visible') loadIdentity() }
onMounted(() => { refresh(); window.addEventListener('focus', refreshIdentity); document.addEventListener('visibilitychange', refreshIdentity) })
onUnmounted(() => { health.cancel(); modules.cancel(); identity.cancel(); window.removeEventListener('focus', refreshIdentity); document.removeEventListener('visibilitychange', refreshIdentity) })
</script>
<template>
  <AuthLayout v-if="route.page === 'login'">
    <p v-if="!identityChecked" class="auth-check" role="status">正在确认登录状态…</p>
    <LoginPage v-else-if="!identity.data.value?.authenticated" @authenticated="loadIdentity" />
  </AuthLayout>
  <AppLayout v-else :page="route.page" :title="route.title" :path="route.path" :platform="health.data.value?.platform || 'Runtu Platform'" @refresh="refresh">
    <template #account><UserMenu :identity="identity.data.value" :pending="identity.pending.value" :unavailable="Boolean(identity.error.value)" @signed-out="signedOut" @refresh-identity="loadIdentity" /></template>
    <DashboardPage v-if="route.page === 'dashboard'" :health="health" :modules="modules" />
    <ModulesPage v-else-if="route.page === 'modules'" :modules="modules" :module-id="route.moduleId" />
    <SettingsPage v-else-if="route.page === 'settings'" />
    <NotFoundPage v-else />
  </AppLayout>
</template>

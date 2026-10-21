<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import AuthLayout from './components/AuthLayout.vue'
import LoginPage from './pages/LoginPage.vue'
import { asyncView } from './components/asyncView.js'
import { readIdentity } from './api/auth.js'
import { readAccess } from './api/access.js'
import { provideNavigation } from './navigation/context.js'
import { useResource } from './composables/useResource.js'
import { readHealth, readModules } from './api/client.js'
const AppLayout = asyncView(() => import('./components/AppLayout.vue'))
const UserMenu = asyncView(() => import('./components/UserMenu.vue'))
const DashboardPage = asyncView(() => import('./pages/DashboardPage.vue'))
const ModulesPage = asyncView(() => import('./pages/ModulesPage.vue'))
const SettingsPage = asyncView(() => import('./pages/SettingsPage.vue'))
const UsersPage = asyncView(() => import('./pages/UsersPage.vue'))
const RegisterPage = asyncView(() => import('./pages/RegisterPage.vue'))
const NotFoundPage = asyncView(() => import('./pages/NotFoundPage.vue'))
const { route, navigate } = provideNavigation()
const health = useResource(readHealth), modules = useResource(readModules)
const identity = useResource(readIdentity)
const access = useResource(readAccess)
const directoryModules = { ...modules, data: computed(() => modules.data.value?.filter(item =>
  item.access_mode !== 'assigned' || access.data.value?.permissions.includes('module.manage')) ?? null) }
watch(() => identity.data.value?.authenticated ? identity.data.value.user.id : null, (id) => {
  if (id) access.load()
  else { access.cancel(); access.data.value = null; access.error.value = null }
})
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
onUnmounted(() => { health.cancel(); modules.cancel(); identity.cancel(); access.cancel(); window.removeEventListener('focus', refreshIdentity); document.removeEventListener('visibilitychange', refreshIdentity) })
</script>
<template>
  <AuthLayout v-if="route.page === 'login' || route.page === 'register'">
    <p v-if="!identityChecked" class="auth-check" role="status">正在确认登录状态…</p>
    <RegisterPage v-else-if="route.page === 'register'" />
    <LoginPage v-else-if="!identity.data.value?.authenticated" @authenticated="loadIdentity" />
  </AuthLayout>
  <AppLayout v-else :page="route.page" :title="route.title" :path="route.path" :can-manage-users="Boolean(access.data.value?.permissions.includes('users.manage'))" :platform="health.data.value?.platform || 'Runtu Platform'" @refresh="refresh">
    <template #account><UserMenu :identity="identity.data.value" :access="access" :pending="identity.pending.value" :unavailable="Boolean(identity.error.value)" @signed-out="signedOut" @refresh-identity="loadIdentity" /></template>
    <DashboardPage v-if="route.page === 'dashboard'" :health="health" :modules="directoryModules" :user-id="identity.data.value?.user?.id" />
    <ModulesPage v-else-if="route.page === 'modules'" :modules="directoryModules" :module-id="route.moduleId" :access="access" @changed="modules.load()" />
    <SettingsPage v-else-if="route.page === 'settings'" :access="access" />
    <UsersPage v-else-if="route.page === 'users'" :access="access" :self-id="identity.data.value?.user?.id" />
    <NotFoundPage v-else />
  </AppLayout>
</template>

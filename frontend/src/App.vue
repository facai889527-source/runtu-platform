<script setup>
import { computed, shallowRef, watch, onMounted, onUnmounted } from 'vue'
import { loginPath, returnTarget } from './navigation/history.js'
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
const NotificationsPage = asyncView(() => import('./pages/NotificationsPage.vue'))
const UsersPage = asyncView(() => import('./pages/UsersPage.vue'))
const RegisterPage = asyncView(() => import('./pages/RegisterPage.vue'))
const NotFoundPage = asyncView(() => import('./pages/NotFoundPage.vue'))
const { route, navigate } = provideNavigation()
const health = useResource(readHealth), modules = useResource(readModules)
const identity = useResource(readIdentity, { retainData: true })
// Keep same-account dialogs/drafts mounted during focus revalidation. Errors clear access.
const access = useResource(readAccess, { retainData: true })
const directoryModules = { ...modules, data: computed(() => modules.data.value?.filter(item =>
  item.access_mode !== 'assigned' || access.data.value?.permissions.includes('module.manage')) ?? null) }
const identityChecked = shallowRef(false)
const authenticated = computed(() => Boolean(identity.data.value?.authenticated))
const publicPage = computed(() => ['login', 'register'].includes(route.value.page))
const canManageUsers = computed(() => authenticated.value && access.data.value?.role === 'owner' && access.data.value.permissions.includes('users.manage'))
const canManageNotifications = computed(() => authenticated.value)
function clearWorkspace() {
  for (const resource of [health, modules, access]) { resource.cancel(); resource.data.value = null; resource.error.value = null }
}
async function loadIdentity() {
  await identity.load(); identityChecked.value = true
  if (authenticated.value) access.load()
}
watch(() => authenticated.value ? identity.data.value?.user?.id : null, value => {
  clearWorkspace()
  if (value) { health.load(); modules.load() }
})
watch(() => [route.value.page, identity.pending.value, identityChecked.value, authenticated.value], () => {
  if (!identityChecked.value || identity.pending.value || identity.error.value) return
  if (!authenticated.value && !publicPage.value) navigate(loginPath(route.value.path), { replace: true })
  else if (authenticated.value && route.value.page === 'login') navigate(returnTarget(window.location.search), { replace: true })
})
function sessionExpired() {
  identity.cancel(); identity.data.value = { authenticated: false, user: null }; identity.error.value = null
  identityChecked.value = true; clearWorkspace()
  if (!publicPage.value) navigate(loginPath(route.value.path), { replace: true })
}
async function signedOut() { sessionExpired(); navigate('/login', { replace: true }) }
function refresh() { loadIdentity(); if (authenticated.value) { health.load(); modules.load() } }
function refreshIdentity() { if (document.visibilityState === 'visible') loadIdentity() }
onMounted(() => { loadIdentity(); window.addEventListener('focus', refreshIdentity); document.addEventListener('visibilitychange', refreshIdentity); window.addEventListener('runtu-session-expired', sessionExpired) })
onUnmounted(() => { clearWorkspace(); identity.cancel(); window.removeEventListener('focus', refreshIdentity); document.removeEventListener('visibilitychange', refreshIdentity); window.removeEventListener('runtu-session-expired', sessionExpired) })
</script>
<template>
  <AuthLayout v-if="publicPage || !authenticated">
    <p v-if="!identityChecked || (!publicPage && identity.pending.value)" class="auth-check" role="status">正在确认登录状态…</p>
    <div v-else-if="!publicPage && identity.error.value" role="alert"><h1>身份暂无法确认</h1><button @click="loadIdentity">重试身份查询</button></div>
    <RegisterPage v-else-if="route.page === 'register'" />
    <LoginPage v-else-if="!authenticated" @authenticated="loadIdentity" />
  </AuthLayout>
  <AppLayout v-else :page="route.page" :title="route.title" :path="route.path" :user-id="identity.data.value?.user?.id" :can-manage-users="Boolean(canManageUsers)" :can-manage-notifications="Boolean(canManageNotifications)" :can-manage-settings="Boolean(canManageUsers || access.data.value?.permissions.includes('module.manage'))" :platform="health.data.value?.platform || 'Runtu Platform'" @refresh="refresh">
    <template #account><UserMenu :identity="identity.data.value" :access="access" :pending="identity.pending.value" :unavailable="Boolean(identity.error.value)" @signed-out="signedOut" @refresh-identity="loadIdentity" /></template>
    <DashboardPage v-if="['dashboard', 'tools'].includes(route.page)" :health="health" :modules="directoryModules" :user-id="identity.data.value?.user?.id" :user="identity.data.value?.user" :access="access" :show-diagnostics="access.data.value?.role === 'owner'" />
    <ModulesPage v-else-if="route.page === 'modules' && route.moduleId" :modules="directoryModules" :module-id="route.moduleId" :access="access" @changed="modules.load()" />
    <SettingsPage v-else-if="route.page === 'settings' || route.page === 'modules'" :access="access" :modules="directoryModules" @changed="modules.load()" />
    <UsersPage v-else-if="route.page === 'users' && canManageUsers" :access="access" :self-id="identity.data.value?.user?.id" />
    <p v-else-if="route.page === 'users'" role="status">{{ access.pending.value ? '正在确认用户管理权限…' : '当前身份没有用户管理权限。' }}</p>
    <NotificationsPage v-else-if="route.page === 'notifications' && canManageNotifications" :key="identity.data.value?.user?.id" />
    <p v-else-if="route.page === 'notifications'" role="status">{{ access.pending.value ? '正在确认消息设置权限…' : '当前身份没有消息设置权限。' }}</p>
    <NotFoundPage v-else />
  </AppLayout>
</template>

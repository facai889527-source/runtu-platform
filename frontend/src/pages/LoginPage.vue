<script setup>
import { ref, onUnmounted } from 'vue'
import RouteLink from '../components/RouteLink.vue'
import { useNavigation } from '../navigation/context.js'
import { login } from '../api/auth.js'
const emit = defineEmits(['authenticated'])
const { navigate } = useNavigation()
const username = ref(''), password = ref(''), pending = ref(false), error = ref('')
let controller, timer
async function submit() {
  if (pending.value) return
  pending.value = true; error.value = ''
  controller = new AbortController()
  timer = setTimeout(() => controller.abort(), 10000)
  // Clear the bound field immediately; no credential persistence or logging.
  const operation = login(username.value, password.value, controller.signal)
  password.value = ''
  try {
    const result = await operation
    if (!result.authenticated) throw new Error('未能确认登录状态，请重试。')
    emit('authenticated')
    navigate('/')
  } catch (failure) {
    error.value = failure.name === 'AbortError' ? '请求超时，请重新确认登录状态后重试。' : failure.message || '网络连接失败，请稍后重试。'
  } finally { clearTimeout(timer); pending.value = false }
}
onUnmounted(() => { clearTimeout(timer); controller?.abort(); password.value = '' })
</script>
<template>
  <section class="login-panel" aria-labelledby="login-title">
    <div class="login-context"><span class="login-rule" aria-hidden="true" /><h2 id="login-title">连接你的管理员身份</h2><p>使用本地初始化的管理员账户登录。</p><p class="login-boundary">当前工作台仅提供信息浏览。登录验证身份，管理写入能力尚未开放。</p><RouteLink to="/">继续匿名浏览</RouteLink></div>
    <form class="login-form" @submit.prevent="submit" :aria-busy="pending">
      <label for="login-username">用户名</label>
      <input id="login-username" v-model="username" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" required maxlength="64" :disabled="pending" />
      <label for="login-password">密码</label>
      <input id="login-password" v-model="password" name="password" type="password" autocomplete="current-password" required maxlength="128" :disabled="pending" />
      <p v-if="error" class="auth-error" role="alert">{{ error }}</p>
      <button type="submit" class="login-submit" :disabled="pending">{{ pending ? '正在验证…' : '登录' }}</button>
      <p class="login-help">没有账户？请联系受控本地操作员完成首次初始化。平台不提供公开注册。</p>
    </form>
  </section>
</template>
<style scoped>
.login-panel { display: grid; grid-template-columns: 1fr 1fr; max-width: 960px; margin: 24px 0; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
.login-context { padding: 36px; background: #edf4f5; }
.login-rule { display: block; width: 36px; height: 4px; margin-bottom: 24px; background: var(--accent); }
.login-context h2 { font-size: 24px; line-height: 1.5; margin-bottom: 16px; }
.login-boundary { margin: 24px 0; color: #455d69; }
.login-form { display: flex; flex-direction: column; gap: 10px; padding: 36px; }
.login-form label { font-weight: 600; }
.login-form input { width: 100%; min-height: 46px; border: 1px solid var(--line-strong); border-radius: 8px; background: white; padding: 10px 12px; margin-bottom: 12px; color: var(--ink); }
.login-submit { background: var(--accent); color: white; border-color: var(--accent); margin-top: 6px; }
.login-submit:hover { background: var(--accent-hover); color: white; }
.login-help { color: #526873; font-size: 12px; margin: 10px 0 0; }
.auth-error { color: var(--danger); margin: 0; }
@media (max-width: 760px) { .login-panel { grid-template-columns: 1fr; margin-top: 16px; } .login-context, .login-form { padding: 24px; } .login-context h2 { font-size: 21px; } }
</style>

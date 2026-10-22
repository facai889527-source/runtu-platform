<script setup>
import { ref, onUnmounted } from 'vue'
import { useNavigation } from '../navigation/context.js'
import { readPublicPolicy } from '../api/registration.js'
import { login } from '../api/auth.js'
const emit = defineEmits(['authenticated'])
const username = ref(''), password = ref(''), pending = ref(false), error = ref('')
const { navigate } = useNavigation()
const signupPending = ref(false), signupMessage = ref('')
let signupController, signupTimer, live = true, cachedPolicy, checkedAt = 0
let controller, timer
async function signup() {
  if (pending.value || signupPending.value) return
  signupMessage.value = ''
  if (cachedPolicy && Date.now() - checkedAt < 10000) {
    if (cachedPolicy.enabled) navigate('/register')
    else signupMessage.value = '暂未开放注册'
    return
  }
  signupPending.value = true; signupController = new AbortController()
  signupTimer = setTimeout(() => signupController.abort(), 8000)
  try {
    const policy = await readPublicPolicy(signupController.signal)
    if (!live) return
    cachedPolicy = policy; checkedAt = Date.now()
    if (policy.enabled) navigate('/register')
    else signupMessage.value = '暂未开放注册'
  } catch { if (live) signupMessage.value = '注册服务暂不可用，请稍后再试' }
  finally { clearTimeout(signupTimer); if (live) signupPending.value = false }
}
async function submit() {
  if (pending.value || signupPending.value) return
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
  } catch (failure) {
    error.value = failure.name === 'AbortError' ? '请求超时，请重新确认登录状态后重试。' : failure.message || '网络连接失败，请稍后重试。'
  } finally { clearTimeout(timer); pending.value = false }
}
onUnmounted(() => { live = false; clearTimeout(timer); controller?.abort(); clearTimeout(signupTimer); signupController?.abort(); password.value = '' })
</script>
<template>
  <section class="login-panel" aria-labelledby="login-title">
    <div class="login-context"><h1 id="login-title">登录管理后台</h1><p>使用你的平台账户继续。</p></div>
    <form class="login-form" @submit.prevent="submit" :aria-busy="pending">
      <label for="login-username">用户名</label>
      <input id="login-username" v-model="username" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" required maxlength="64" :disabled="pending" />
      <label for="login-password">密码</label>
      <input id="login-password" v-model="password" name="password" type="password" autocomplete="current-password" required maxlength="128" :disabled="pending" />
      <p v-if="error" class="auth-error" role="alert">{{ error }}</p>
      <button type="submit" class="login-submit" :disabled="pending || signupPending">{{ pending ? '正在验证…' : '登录' }}</button>
      <p class="login-help">没有账户？ <a href="/register" :aria-disabled="pending || signupPending" @click.prevent="signup">申请注册账号</a></p>
      <p v-if="signupPending || signupMessage" class="signup-notice" role="status" aria-live="polite">{{ signupPending ? '正在确认注册状态…' : signupMessage }}</p>
    </form>
  </section>
</template>
<style scoped>
.login-panel { width: 100%; }
.login-context { margin-bottom: 32px; }
.login-context p { color: var(--auth-muted); margin: 0; font-size: 14px; line-height: 1.8; }
.login-form { display: flex; flex-direction: column; gap: 10px; }
.login-form label { font-size: 13px; font-weight: 600; }
.login-form input { margin-bottom: 14px; }
.login-submit { margin-top: 6px; }
.login-help { margin: 14px 0 0; color: var(--auth-muted); text-align: center; font-size: 13px; line-height: 2; }
.login-help a { display: inline-flex; align-items: center; min-height: 44px; font-weight: 600; }
.auth-error { margin: 0; }
.signup-notice { margin: 0; text-align: center; color: var(--auth-muted); font-size: 13px; line-height: 1.8; }
.login-help a[aria-disabled=true] { opacity: .65; cursor: wait; }
</style>

<script setup>
import { ref, useTemplateRef, onMounted, onUnmounted } from 'vue'
import RouteLink from '../components/RouteLink.vue'
import { readPublicPolicy, register } from '../api/registration.js'
const policy = ref(null), username = ref(''), busy = ref(false), error = ref(''), submitted = ref(false)
const passwordInput = useTemplateRef('passwordInput')
let controller, timer, live = true
async function load() {
  if (busy.value) return
  busy.value = true; error.value = ''; policy.value = null
  controller = new AbortController(); timer = setTimeout(() => controller.abort(), 10000)
  try { const value = await readPublicPolicy(controller.signal); if (live) policy.value = value }
  catch (cause) { if (live) error.value = cause.name === 'AbortError' ? '注册状态查询超时，请重试。' : cause.message }
  finally { clearTimeout(timer); if (live) busy.value = false }
}
async function submit() {
  if (busy.value || !policy.value?.enabled) return
  const password = passwordInput.value.value; passwordInput.value.value = ''
  busy.value = true; error.value = ''; controller = new AbortController(); timer = setTimeout(() => controller.abort(), 10000)
  try { await register(username.value, password, controller.signal); if (live) { submitted.value = true; username.value = '' } }
  catch (cause) { if (live) error.value = cause.name === 'AbortError' ? '提交结果未确认，请联系管理员后再决定是否重试。' : cause.message }
  finally { clearTimeout(timer); if (passwordInput.value) passwordInput.value.value = ''; if (live) busy.value = false }
}
onMounted(load)
onUnmounted(() => { live = false; controller?.abort(); clearTimeout(timer); if (passwordInput.value) passwordInput.value.value = '' })
</script>
<template>
  <section class="register-panel" aria-labelledby="register-title"><h1 id="register-title">申请平台账户</h1>
    <p class="subtle">新账户为只读成员，业务模块需要管理员另行授权。</p>
    <p v-if="busy" role="status">正在处理…</p>
    <div v-if="submitted" role="status"><h2>申请已提交</h2><p>如该用户名可用且需要审核，新申请将处于待审核状态，批准前无法登录。已有账户不会被重复创建或更改。</p><p>请联系管理员确认。若注册时无需审核，可使用新账户登录。</p></div>
    <div v-else-if="policy && !policy.enabled" class="registration-closed" role="status"><span class="closed-symbol" aria-hidden="true">—</span><h2>管理员暂未开放注册</h2><p>请联系平台管理员了解开放安排，或使用已有账户返回登录。</p></div>
    <form v-else-if="policy?.enabled" @submit.prevent="submit"><fieldset :disabled="busy"><legend class="subtle">{{ policy.approval_required ? '需要所有者审核，批准前无法登录。' : '无需审核，账户创建后可登录。' }}</legend>
      <label>用户名<input v-model="username" required minlength="3" maxlength="64" pattern="[a-z0-9_.\-]{3,64}" autocomplete="username" autocapitalize="none" spellcheck="false" /></label>
      <label>密码<input ref="passwordInput" type="password" required minlength="14" maxlength="128" autocomplete="new-password" /></label>
      <button type="submit">提交注册申请</button>
    </fieldset></form>
    <p v-if="error" role="alert">{{ error }}</p><button v-if="!submitted" :disabled="busy" @click="load">刷新注册状态</button>
    <RouteLink to="/login" class="login-link">返回登录</RouteLink>
  </section>
</template>
<style scoped>
.register-panel { width: 100%; } .register-panel > .subtle { color: var(--auth-muted); font-size: 14px; line-height: 1.8; margin-bottom: 24px; }
.register-panel fieldset { border: 0; padding: 0; margin: 24px 0; display: grid; gap: 18px; min-width: 0; }
.register-panel legend { margin-bottom: 18px; font-size: 13px; line-height: 1.8; color: var(--auth-muted); }
.register-panel label { display: grid; gap: 9px; font-size: 13px; font-weight: 600; }
.registration-closed { padding: 24px 20px; margin: 28px 0 22px; border-radius: 14px; background: #eef5f3; border: 1px solid #c5dad3; }
.closed-symbol { display: inline-grid; place-items: center; width: 32px; height: 32px; background: #d8e9e3; color: #2e6255; border-radius: 50%; margin-bottom: 14px; font-weight: 650; }
.registration-closed h2 { font-size: 17px; color: var(--auth-navy); margin: 0 0 10px; }
.registration-closed p { color: var(--auth-muted); margin: 0; line-height: 1.8; font-size: 13px; }
.login-link { display: flex; align-items: center; justify-content: center; margin-top: 16px; min-height: 44px; font-size: 13px; }
</style>

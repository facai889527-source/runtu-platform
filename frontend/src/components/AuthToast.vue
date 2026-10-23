<script setup>
import { shallowRef, watch, onUnmounted } from 'vue'
const props = defineProps({ notice: Object })
const visible = shallowRef(false)
let timer
function dismiss() { clearTimeout(timer); visible.value = false }
watch(() => props.notice, value => {
  dismiss()
  if (value) { visible.value = true; timer = setTimeout(dismiss, 3200) }
}, { immediate: true })
onUnmounted(() => clearTimeout(timer))
</script>
<template>
  <div class="auth-toast-region" role="status" aria-live="polite" aria-atomic="true">
    <Transition name="auth-toast">
      <div v-if="visible" class="auth-toast">
        <svg class="toast-symbol" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.5" /><path d="M12 11v5m0-9v.1" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" /></svg>
        <span>{{ notice.message }}</span><button type="button" aria-label="关闭提示" @click="dismiss">×</button>
      </div>
    </Transition>
  </div>
</template>
<style scoped>
.auth-toast-region { position: fixed; z-index: 100; bottom: 28px; left: 50%; transform: translateX(-50%); width: max-content; max-width: calc(100vw - 32px); pointer-events: none; }
.auth-toast { display: flex; align-items: center; gap: 12px; min-height: 64px; padding: 10px 10px 10px 18px; border: 1px solid #cbdad3; border-radius: 14px; background: #fffffc; color: #223b35; box-shadow: 0 12px 40px #172b3526, 0 2px 6px #172b350a; pointer-events: auto; font-size: 14px; line-height: 1.65; }
.toast-symbol { width: 24px; height: 24px; color: #176d58; flex-shrink: 0; }
.auth-toast span { max-width: 320px; overflow-wrap: anywhere; }
.auth-toast button { width: 44px; height: 44px; min-height: 44px; padding: 0; border: 0; background: transparent; color: #526873; font-size: 23px; flex-shrink: 0; }
.auth-toast button:hover { background: #edf3ef; color: #172b35; }
.auth-toast button:focus-visible { outline: 3px solid #176d58; outline-offset: 1px; }
.auth-toast-enter-active { transition: opacity .2s ease, transform .2s ease; }
.auth-toast-leave-active { transition: opacity .18s ease, transform .18s ease; }
.auth-toast-enter-from, .auth-toast-leave-to { opacity: 0; transform: translateY(10px); }
@media (max-width: 760px) { .auth-toast-region { bottom: 20px; width: calc(100vw - 32px); } .auth-toast { font-size: 13px; gap: 10px; padding-left: 14px; } .auth-toast span { flex: 1; } }
@media (prefers-reduced-motion: reduce) { .auth-toast-enter-active, .auth-toast-leave-active { transition: none; } .auth-toast-enter-from, .auth-toast-leave-to { transform: none; } }
</style>

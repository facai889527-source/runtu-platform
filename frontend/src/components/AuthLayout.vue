<script setup>
import { onMounted } from 'vue'
import BrandMark from './BrandMark.vue'
onMounted(() => { document.title = '管理员登录 · Runtu Platform' })
</script>

<template>
  <div class="auth-layout">
    <header class="auth-brand"><BrandMark /><span>Runtu <small>模块化管理平台</small></span></header>
    <main class="auth-main" id="auth-content"><slot /></main>
    <div class="auth-footer">Runtu Platform</div>
  </div>
</template>

<style scoped>
.auth-layout { min-height: 100dvh; display: flex; flex-direction: column; border-top: 4px solid var(--accent); background: var(--canvas); }
.auth-brand { display: flex; align-items: center; gap: 12px; padding: 28px 40px; color: var(--sidebar); font-size: 23px; font-weight: 650; }
.auth-brand small { display: block; font-size: 12px; font-weight: 400; margin-top: 3px; }
.auth-main { width: 100%; max-width: 480px; margin: auto; padding: 32px 24px 56px; }
.auth-footer { color: var(--muted); text-align: center; font-size: 12px; padding: 20px; }
@media (max-width: 760px) { .auth-brand { padding: 24px; } .auth-main { padding: 24px 20px 40px; } }
</style>

<script setup>
import { watchEffect } from 'vue'
import BrandMark from './BrandMark.vue'
import { useNavigation } from '../navigation/context.js'
const { route } = useNavigation()
watchEffect(() => { document.title = `${route.value.page === 'register' ? '申请注册账号' : '账户登录'} · Runtu Platform` })
</script>

<template>
  <div class="auth-layout">
    <div class="auth-shell">
      <aside class="auth-story" aria-label="Runtu 平台">
        <header class="auth-brand"><BrandMark /><span>Runtu<small>润土工具平台</small></span></header>
        <div class="auth-intro"><h2>常用工具，<br />一个入口。</h2><p>润土汇聚实用工具，<br />让日常工作有序展开。</p></div>
        <p class="auth-story-detail">从这里开始，找到适合你的工具。</p>
      </aside>
      <div class="auth-content">
        <main class="auth-main" id="auth-content"><slot /></main>
        <footer class="auth-footer">Runtu Platform</footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-layout { --auth-dark: #19353b; --auth-navy: #172b35; --auth-light: #f7f6f2; --auth-muted: #56676d; --auth-accent: #176d58; --auth-accent-hover: #125844; min-height: 100dvh; display: grid; place-items: center; padding: 32px; background: radial-gradient(ellipse at 10% 5%, #e6eee7, transparent 50%), var(--auth-light); color: var(--auth-navy); }
.auth-shell { width: min(1040px, 100%); display: grid; grid-template-columns: .92fr 1.08fr; min-height: 600px; border: 1px solid #e0e6e0; border-radius: 24px; overflow: hidden; background: #fff; box-shadow: 0 20px 64px #172b3512, 0 2px 10px #172e3b08; }
.auth-story { position: relative; overflow: hidden; display: flex; flex-direction: column; padding: 40px; color: #fff; background: radial-gradient(ellipse at 0% 0%, #274b46, transparent 75%), linear-gradient(150deg, var(--auth-dark), var(--auth-navy)); }
.auth-brand { display: flex; align-items: center; gap: 13px; font-size: 25px; font-weight: 650; letter-spacing: -.6px; }
.auth-brand :deep(.brand-mark) { width: 42px; height: 42px; color: #337c70; flex-shrink: 0; }
.auth-brand small { display: block; font-size: 11px; font-weight: 400; letter-spacing: 1px; color: #c5dfdc; margin-top: 2px; }
.auth-intro { margin-top: 72px; position: relative; z-index: 1; }
.auth-intro h2 { margin: 0 0 22px; color: #fff; font-size: clamp(30px, 2.8vw, 40px); line-height: 1.35; font-weight: 600; letter-spacing: -1px; }
.auth-intro p { margin: 0; font-size: 15px; line-height: 1.9; color: #c5dfdc; }
.auth-story-detail { margin: auto 0 0; padding-top: 28px; font-size: 12px; line-height: 1.8; color: #c5dfdc; }
.auth-content { display: flex; flex-direction: column; padding: 44px 52px 26px; min-width: 0; }
.auth-main { width: 100%; max-width: 400px; margin: auto; padding: 12px 0 28px; }
.auth-footer { display: flex; justify-content: center; flex-wrap: wrap; gap: 8px; width: 100%; max-width: 400px; margin: 0 auto; color: var(--auth-muted); font-size: 11px; padding-top: 24px; border-top: 1px solid #e4ecee; }
.auth-main :deep(h1) { color: var(--auth-navy); margin: 0 0 10px; font-size: 29px; line-height: 1.4; letter-spacing: -.8px; }
.auth-main :deep(input) { background: #fcfcf9; color: var(--auth-navy); border: 1px solid #7b929d; border-radius: 10px; width: 100%; min-height: 50px; padding: 12px 14px; font-size: 16px; transition: border-color .16s, box-shadow .16s, background .16s; }
.auth-main :deep(input:hover:not(:disabled)) { border-color: #597e84; }
.auth-main :deep(input:focus-visible) { outline: 3px solid #176d5840; outline-offset: 2px; border-color: var(--auth-accent); background: #fff; }
.auth-main :deep(input:disabled) { background: #edf2f4; color: var(--auth-muted); cursor: wait; }
.auth-main :deep(button) { min-height: 48px; border-radius: 10px; font-size: 14px; }
.auth-main :deep(button[type=submit]) { min-height: 50px; background: linear-gradient(110deg, var(--auth-accent), #125844); color: #fff; border-color: #0b6f64; font-weight: 600; box-shadow: 0 5px 14px #176d581c; }
.auth-main :deep(button[type=submit]:hover:not(:disabled)) { background: var(--auth-accent-hover); box-shadow: 0 7px 18px #176d5830; }
.auth-main :deep(button:disabled) { opacity: .65; cursor: wait; box-shadow: none; }
.auth-main :deep(a) { color: #076d64; text-underline-offset: 4px; text-decoration-thickness: 1px; }
.auth-main :deep(a:hover) { color: #034c45; }
.auth-main :deep(a:focus-visible), .auth-main :deep(button:focus-visible) { outline: 3px solid #176d58; outline-offset: 4px; }
.auth-main :deep([role=alert]) { color: #9d3434; background: #fff3f1; border: 1px solid #e4b9b1; border-radius: 10px; padding: 12px 14px; font-size: 13px; line-height: 1.7; overflow-wrap: anywhere; }
@media (max-width: 1000px) and (min-width: 761px) { .auth-layout { padding: 24px; } .auth-story { padding: 32px; } .auth-content { padding: 44px 32px 24px; } }
@media (max-width: 760px) { .auth-layout { padding: 20px 16px; align-items: start; } .auth-shell { display: block; min-height: 0; max-width: 480px; border-radius: 22px; } .auth-story { padding: 23px 24px; } .auth-brand { font-size: 23px; } .auth-brand small { font-size: 10px; } .auth-intro, .auth-story-detail { display: none; } .auth-content { padding: 28px 24px 20px; } .auth-main { padding: 0 0 32px; } .auth-main :deep(h1) { font-size: 26px; } .auth-footer { font-size: 10px; padding-top: 20px; } }
@media (prefers-reduced-motion: reduce) { .auth-main :deep(*) { transition: none; animation: none; } }
</style>

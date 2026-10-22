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
        <header class="auth-brand"><BrandMark /><span>Runtu<small>模块化管理平台</small></span></header>
        <div class="auth-intro"><h2>让工具各司其职，<br />让效率持续提升。</h2><p>一个平台，汇聚多种实用工具。<br />按需使用，持续扩展，<br />让复杂工作变得简单。</p></div>
        <div class="auth-abstract" aria-hidden="true"><span></span><span></span><span></span></div>
      </aside>
      <div class="auth-content">
        <main class="auth-main" id="auth-content"><slot /></main>
        <footer class="auth-footer">Runtu Platform<span>统一入口 · 专注管理</span></footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-layout { --auth-dark: #103f46; --auth-navy: #172e3b; --auth-light: #f3f7f7; --auth-muted: #526873; --auth-accent: #087f75; --auth-accent-hover: #06685f; min-height: 100dvh; display: grid; place-items: center; padding: 40px; background: radial-gradient(ellipse at 6% 10%, #dcebe8, transparent 48%), radial-gradient(ellipse at 95% 100%, #e2e8f0, transparent 50%), var(--auth-light); color: var(--auth-navy); }
.auth-shell { width: min(1120px, 100%); display: grid; grid-template-columns: .94fr 1.06fr; min-height: 680px; border: 1px solid #ffffffb3; border-radius: 28px; overflow: hidden; background: #fff; box-shadow: 0 24px 80px #172e3b16, 0 2px 10px #172e3b08; }
.auth-story { position: relative; overflow: hidden; display: flex; flex-direction: column; padding: 44px; color: #fff; background: radial-gradient(ellipse at 0% 10%, #24625e, transparent 65%), linear-gradient(150deg, var(--auth-dark), var(--auth-navy)); }
.auth-brand { display: flex; align-items: center; gap: 13px; font-size: 25px; font-weight: 650; letter-spacing: -.6px; }
.auth-brand :deep(.brand-mark) { width: 42px; height: 42px; color: #337c70; flex-shrink: 0; }
.auth-brand small { display: block; font-size: 11px; font-weight: 400; letter-spacing: 1px; color: #c5dfdc; margin-top: 2px; }
.auth-intro { margin-top: 64px; position: relative; z-index: 1; }
.auth-intro h2 { margin: 0 0 22px; color: #fff; font-size: clamp(27px, 2.5vw, 36px); line-height: 1.35; font-weight: 600; letter-spacing: -1px; }
.auth-intro p { margin: 0; font-size: 15px; line-height: 1.9; color: #c5dfdc; }
.auth-abstract { position: relative; height: 180px; margin-top: 40px; overflow: hidden; }
.auth-abstract span { position: absolute; width: 290px; height: 100px; border: 1px solid #bde2df30; border-radius: 100%; transform: rotate(-25deg); left: -25px; top: 20px; background: linear-gradient(140deg, #c5dfdc10, transparent 70%); }
.auth-abstract span:nth-child(2) { left: 45px; top: 45px; opacity: .65; }
.auth-abstract span:nth-child(3) { left: 115px; top: 70px; opacity: .35; }
.auth-content { display: flex; flex-direction: column; padding: 60px 56px 28px; min-width: 0; }
.auth-main { width: 100%; max-width: 400px; margin: auto; padding: 20px 0 36px; }
.auth-footer { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; width: 100%; max-width: 400px; margin: 0 auto; color: var(--auth-muted); font-size: 11px; padding-top: 24px; border-top: 1px solid #e4ecee; }
.auth-main :deep(h1) { color: var(--auth-navy); margin: 0 0 10px; font-size: 29px; line-height: 1.4; letter-spacing: -.8px; }
.auth-main :deep(input) { background: #f9fbfc; color: var(--auth-navy); border: 1px solid #7b929d; border-radius: 10px; width: 100%; min-height: 50px; padding: 12px 14px; font-size: 16px; transition: border-color .16s, box-shadow .16s, background .16s; }
.auth-main :deep(input:hover:not(:disabled)) { border-color: #597e84; }
.auth-main :deep(input:focus-visible) { outline: 3px solid #087f7540; outline-offset: 2px; border-color: var(--auth-accent); background: #fff; }
.auth-main :deep(input:disabled) { background: #edf2f4; color: var(--auth-muted); cursor: wait; }
.auth-main :deep(button) { min-height: 48px; border-radius: 10px; font-size: 14px; }
.auth-main :deep(button[type=submit]) { min-height: 50px; background: linear-gradient(110deg, var(--auth-accent), #11665f); color: #fff; border-color: #0b6f64; font-weight: 600; box-shadow: 0 5px 14px #0873631c; }
.auth-main :deep(button[type=submit]:hover:not(:disabled)) { background: var(--auth-accent-hover); box-shadow: 0 7px 18px #08736330; }
.auth-main :deep(button:disabled) { opacity: .65; cursor: wait; box-shadow: none; }
.auth-main :deep(a) { color: #076d64; text-underline-offset: 4px; text-decoration-thickness: 1px; }
.auth-main :deep(a:hover) { color: #034c45; }
.auth-main :deep(a:focus-visible), .auth-main :deep(button:focus-visible) { outline: 3px solid #087f75; outline-offset: 4px; }
.auth-main :deep([role=alert]) { color: #9d3434; background: #fff3f1; border: 1px solid #e4b9b1; border-radius: 10px; padding: 12px 14px; font-size: 13px; line-height: 1.7; overflow-wrap: anywhere; }
@media (max-width: 1000px) and (min-width: 761px) { .auth-layout { padding: 24px; } .auth-story { padding: 32px; } .auth-content { padding: 44px 32px 24px; } }
@media (max-width: 760px) { .auth-layout { padding: 20px 16px; align-items: start; } .auth-shell { display: block; min-height: 0; max-width: 480px; border-radius: 22px; } .auth-story { padding: 23px 24px; } .auth-brand { font-size: 23px; } .auth-brand small { font-size: 10px; } .auth-intro, .auth-abstract { display: none; } .auth-content { padding: 34px 24px 22px; } .auth-main { padding: 0 0 32px; } .auth-main :deep(h1) { font-size: 26px; } .auth-footer { font-size: 10px; padding-top: 20px; } }
@media (prefers-reduced-motion: reduce) { .auth-main :deep(*) { transition: none; animation: none; } }
</style>

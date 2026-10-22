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
        <div class="auth-intro"><h2>让管理，<br />回归清晰。</h2><p>连接模块、账户与权限，<br />从一个有序的工作台开始。</p></div>
        <div class="auth-structure" aria-hidden="true">
          <div class="structure-grid"></div><div class="structure-line"></div>
          <span class="structure-node node-module"><i></i>模块</span>
          <span class="structure-node node-account"><i></i>账户</span>
          <span class="structure-node node-access"><i></i>权限</span>
          <span class="structure-center"><BrandMark /></span>
        </div>
        <p class="auth-story-note">各有所属，自有秩序。</p>
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
.auth-intro h2 { margin: 0 0 22px; color: #fff; font-size: clamp(32px, 3.3vw, 46px); line-height: 1.35; font-weight: 600; letter-spacing: -1.5px; }
.auth-intro p { margin: 0; font-size: 15px; line-height: 1.9; color: #c5dfdc; }
.auth-structure { position: relative; height: 185px; margin: 28px -8px 0; }
.structure-grid { position: absolute; inset: -20px -100px -60px; opacity: .13; transform: perspective(400px) rotateX(48deg) rotateZ(-16deg); background-image: linear-gradient(#bde2df 1px, transparent 1px), linear-gradient(90deg, #bde2df 1px, transparent 1px); background-size: 38px 38px; mask-image: radial-gradient(ellipse, #000, transparent 65%); }
.structure-line { position: absolute; width: 65%; height: 84px; top: 52px; left: 17%; border: 1px solid #8ac4b64d; border-radius: 32px; transform: rotate(-14deg); }
.structure-center { position: absolute; left: 40%; top: 49px; width: 70px; height: 70px; display: grid; place-items: center; background: #c7e8db; border: 1px solid #e7fff2; border-radius: 21px; transform: rotate(-8deg); box-shadow: 0 16px 34px #071e3080; }
.structure-center :deep(.brand-mark) { width: 44px; height: 44px; color: #176957; transform: rotate(8deg); }
.structure-node { position: absolute; display: flex; align-items: center; gap: 9px; padding: 12px 18px; border: 1px solid #bddfd04d; border-radius: 12px; background: #294d52; color: #e4f2ee; font-size: 12px; box-shadow: 0 10px 24px #071e3026; }
.structure-node i { width: 6px; height: 6px; background: #9ce2c9; border-radius: 2px; }
.node-module { top: 28px; left: 2%; transform: rotate(-6deg); } .node-account { bottom: 12px; left: 19%; transform: rotate(4deg); } .node-access { top: 55px; right: 0; transform: rotate(6deg); }
.auth-story-note { margin: auto 0 0; padding-top: 20px; font-size: 12px; color: #c5dfdc; }
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
@media (max-width: 760px) { .auth-layout { padding: 20px 16px; align-items: start; } .auth-shell { display: block; min-height: 0; max-width: 480px; border-radius: 22px; } .auth-story { padding: 23px 24px; } .auth-brand { font-size: 23px; } .auth-brand small { font-size: 10px; } .auth-intro, .auth-structure, .auth-story-note { display: none; } .auth-content { padding: 34px 24px 22px; } .auth-main { padding: 0 0 32px; } .auth-main :deep(h1) { font-size: 26px; } .auth-footer { font-size: 10px; padding-top: 20px; } }
@media (prefers-reduced-motion: reduce) { .auth-main :deep(*) { transition: none; animation: none; } }
</style>

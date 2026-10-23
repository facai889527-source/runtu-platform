<script setup>
import { onMounted, onBeforeMount, onBeforeUnmount, onUnmounted, useTemplateRef } from 'vue'
const props=defineProps({title:String,description:String,busy:Boolean})
const emit=defineEmits(['close']), dialog=useTemplateRef('dialog')
let trigger,triggerLabel,overflow
function close(){if(!props.busy)emit('close')}
function backdrop(e){if(e.target===dialog.value){const r=dialog.value.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)close()}}
onBeforeMount(()=>{trigger=document.activeElement;triggerLabel=trigger?.getAttribute('aria-label')})
onMounted(()=>{overflow=document.body.style.overflow;document.body.style.overflow='hidden';dialog.value.showModal();dialog.value.querySelector('[autofocus]')?.focus()})
onBeforeUnmount(()=>{dialog.value?.close();document.body.style.overflow=overflow})
onUnmounted(()=>{requestAnimationFrame(()=>{const target=trigger?.isConnected?trigger:triggerLabel?document.querySelector(`[aria-label="${CSS.escape(triggerLabel)}"]`):document.querySelector('.directory-create');target?.focus()})})
</script>
<template>
<Teleport to="body">
<dialog ref="dialog" class="user-dialog" aria-labelledby="user-dialog-title" aria-describedby="user-dialog-description" :aria-busy="busy" @cancel.prevent="close" @click="backdrop">
<header class="user-dialog-heading">
<div>
<h2 id="user-dialog-title">{{title}}</h2>
<p id="user-dialog-description">{{description}}</p>
</div>
<button type="button" class="dialog-close" aria-label="关闭弹窗" :disabled="busy" @click="close">×</button>
</header>
<div class="user-dialog-content">
<slot />
</div>
</dialog>
</Teleport>
</template>
<style>
.user-dialog{width:min(600px,calc(100% - 40px));max-height:calc(100dvh - 48px);padding:0;border:1px solid #dbe5e4;border-radius:18px;background:#fff;color:var(--ink);box-shadow:0 24px 90px #173b3e38;overflow:auto;overscroll-behavior:contain}.user-dialog[open]{animation:user-dialog-in 180ms ease-out}.user-dialog::backdrop{background:#172e3c66;backdrop-filter:blur(3px);animation:user-backdrop-in 180ms ease-out}.user-dialog-heading{display:flex;align-items:flex-start;gap:16px;padding:26px 28px 20px;border-bottom:1px solid var(--line)}.user-dialog-heading>div{flex:1;min-width:0}.user-dialog-heading h2{font-size:22px;letter-spacing:-.03em;overflow-wrap:anywhere}.user-dialog-heading p{color:var(--muted);font-size:13px;margin:6px 0 0}.dialog-close{border:0;font-size:26px;line-height:1;padding:0;width:44px;flex-shrink:0;color:var(--muted)}.user-dialog-content{padding:24px 28px 28px}
.user-form{display:grid;gap:20px}.user-form fieldset{display:grid;gap:20px;padding:0;margin:0;border:0;min-width:0}.user-form label:not(.user-toggle){display:grid;gap:8px;font-weight:550;font-size:13px}.user-form input:not([type=checkbox]),.user-form select{width:100%;min-width:0;min-height:46px}.user-form small{font-size:12px;font-weight:400;line-height:1.7}.user-select{appearance:none;padding-right:36px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%235a716c' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center}
.user-primary{background:var(--accent);border-color:var(--accent);color:white}.user-primary:hover{background:var(--accent-hover);border-color:var(--accent-hover)}.user-dialog-actions{display:flex;gap:10px;justify-content:flex-end;padding-top:20px;border-top:1px solid var(--line);margin-top:4px}.user-form-error{color:var(--danger);background:var(--danger-soft);padding:12px 14px;border-radius:8px;font-size:13px;margin:0}.user-guidance{padding:13px 16px;border-radius:9px;background:#f0f6f4;color:#45645e;font-size:12px;line-height:1.8;margin:0}.user-confirm{display:grid;gap:12px;padding:16px;background:var(--warning-soft);border:1px solid #e6d6b7;border-radius:9px}.user-confirm p{margin:0;font-size:13px}.user-confirm>div{display:flex;gap:10px;flex-wrap:wrap}.user-toggle{display:flex;align-items:center;gap:12px;font-size:13px}.user-toggle input{width:36px;height:20px;min-height:20px;accent-color:var(--accent);flex-shrink:0}.user-toggle small{display:block;color:var(--muted)}
.user-toggle input[role=switch]{appearance:none;position:relative;border:1px solid #8eaaa4;border-radius:20px;background:#a5b3af;width:38px;height:22px;min-height:22px;padding:0;cursor:pointer;transition:background 180ms}.user-toggle input[role=switch]::before{content:"";position:absolute;width:16px;height:16px;border-radius:50%;background:white;top:2px;left:2px;box-shadow:0 1px 3px #173b3e25;transition:transform 180ms}.user-toggle input[role=switch]:checked{background:var(--accent);border-color:var(--accent)}.user-toggle input[role=switch]:checked::before{transform:translateX(16px)}.user-toggle input[role=switch]:disabled{cursor:default;opacity:.6}
@keyframes user-dialog-in{from{opacity:0;transform:translateY(8px) scale(.99)}to{opacity:1;transform:none}}@keyframes user-backdrop-in{from{opacity:0}to{opacity:1}}@media(max-width:600px){.user-dialog{width:calc(100% - 24px);max-height:calc(100dvh - 24px);border-radius:14px}.user-dialog-heading{padding:20px 20px 16px}.user-dialog-content{padding:20px}.user-dialog-heading h2{font-size:20px}.user-dialog-actions>*{flex:1}}@media(prefers-reduced-motion:reduce){.user-dialog[open],.user-dialog::backdrop{animation:none}.user-toggle input[role=switch],.user-toggle input[role=switch]::before{transition:none}}
</style>

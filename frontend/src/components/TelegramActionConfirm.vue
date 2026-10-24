<script setup>
import { ref, watch, nextTick, onUnmounted } from 'vue'
const props=defineProps({action:String}),emit=defineEmits(['confirm','cancel']),dialog=ref(null)
let previous
watch(()=>props.action,async value=>{await nextTick();if(value){previous=document.activeElement;dialog.value?.showModal()}else{dialog.value?.close();if(previous?.isConnected)previous.focus()}},{flush:'post'})
onUnmounted(()=>dialog.value?.close())
</script>
<template><dialog ref="dialog" class="telegram-confirm-dialog" aria-labelledby="telegram-confirm-title" @cancel.prevent="emit('cancel')"><h3 id="telegram-confirm-title">确认{{action==='disconnect'?'断开连接':action==='rotate'?'重新加密':action==='connect'?'重新验证':'更换 Bot'}}？</h3><p>{{action==='rotate'?'使用当前密钥重新加密，身份和偏好保持不变。':'此操作可能清除身份、接收目标和订阅。平台 Bot 变更也会使其他账户的公共连接失效，请确认后继续。'}}</p><div><button type="button" autofocus @click="emit('cancel')">取消</button><button type="button" class="confirm-action" @click="emit('confirm')">确认继续</button></div></dialog></template>
<style scoped>.telegram-confirm-dialog{box-sizing:border-box;width:min(440px,calc(100% - 32px));padding:26px;border:1px solid #cad8dc;border-radius:12px;background:var(--surface);color:var(--ink);box-shadow:0 18px 80px #142a4333}.telegram-confirm-dialog::backdrop{background:#142a4355}h3{font-size:18px;margin:0 0 12px}p{font-size:13px;line-height:1.8;color:var(--muted);margin:0 0 22px}div{display:flex;justify-content:flex-end;gap:10px}button{min-height:42px;padding:0 18px;border:1px solid #ccd9dd;background:white;border-radius:7px;color:var(--ink);font:inherit;font-size:12px;cursor:pointer}.confirm-action{color:var(--danger);border-color:var(--danger)}button:focus-visible{outline:3px solid var(--focus);outline-offset:3px}</style>

<script setup>
import { shallowRef, computed } from 'vue'
const props=defineProps({busy:Boolean,canSend:Boolean,cooldown:Boolean,customAvailable:Boolean})
const emit=defineEmits(['send'])
const text=shallowRef('')
const valid=computed(()=>text.value.length<=4096&&(!text.value||!!text.value.trim()))
function send(){if(props.canSend&&!props.busy&&!props.cooldown&&valid.value)emit('send',props.customAvailable&&text.value?text.value:undefined)}
</script>
<template>
 <section class="notification-test" aria-labelledby="test-message-title"><div class="test-heading"><h4 id="test-message-title">测试消息</h4><span>仅发送到当前选中私聊</span></div><label for="telegram-test-message">消息内容<span>可选</span></label><textarea id="telegram-test-message" v-model="text" rows="3" maxlength="4096" :disabled="busy||!customAvailable" placeholder="写一条给自己的测试消息…" aria-describedby="test-message-hint" /><div class="test-footer"><p id="test-message-hint">{{cooldown?'已尝试发送，五分钟后可再次测试。':!customAvailable?'当前服务仅支持默认测试消息。':!valid?'内容不能只有空白，最多4096字符。':!canSend?'先选择私聊目标并保存启用。':'留空发送默认消息；每五分钟最多一次。'}}<span v-if="customAvailable">{{text.length}} / 4096</span></p><button type="button" :disabled="busy||!canSend||cooldown||!valid" @click="send">{{busy?'正在处理…':'发送测试消息'}}</button></div></section>
</template>
<style scoped>
.notification-test{padding:22px 0 0;border-top:1px solid var(--line);min-width:0}.test-heading{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:14px}.test-heading h4{font-size:14px;margin:0}.test-heading>span{font-size:10px;color:var(--muted)}label{display:flex;gap:8px;font-size:12px;margin-bottom:8px}label span{color:var(--muted)}textarea{resize:vertical;display:block;box-sizing:border-box;width:100%;min-height:86px;max-height:230px;padding:12px;border:1px solid #c7d5db;border-radius:7px;background:#fcfdfd;font:inherit;font-size:13px;line-height:1.6;color:var(--ink)}textarea:disabled{background:#f4f6f7}.test-footer{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-top:10px}.test-footer p{margin:0;color:var(--muted);font-size:10px;line-height:1.6}.test-footer p span{display:block}button{min-height:40px;padding:0 16px;border:1px solid var(--accent);border-radius:7px;background:var(--accent);color:white;font:inherit;font-size:12px;white-space:nowrap;cursor:pointer}button:disabled{opacity:.5;cursor:not-allowed}:is(button,textarea):focus-visible{outline:3px solid var(--focus);outline-offset:3px}@media(max-width:600px){.test-heading{align-items:flex-start;flex-direction:column;gap:5px}.test-footer{align-items:flex-start;flex-direction:column}.test-footer button{width:100%}}
</style>

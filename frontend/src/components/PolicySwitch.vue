<script setup>
defineProps({ modelValue: Boolean, label: String, description: String })
defineEmits(['update:modelValue'])
</script>
<template><label class="policy-switch"><span class="switch-copy"><strong>{{ label }}</strong><small>{{ description }}</small></span><span class="switch-control"><input type="checkbox" role="switch" :checked="modelValue" @change="$emit('update:modelValue', $event.target.checked)" /><span class="switch-track" aria-hidden="true" /></span></label></template>
<style scoped>
.policy-switch{display:flex;justify-content:space-between;align-items:center;gap:24px;padding:18px 0;border-bottom:1px solid var(--line);cursor:pointer}.switch-copy{display:grid;gap:6px}.switch-copy strong{font-weight:550;font-size:14px}.switch-copy small{font-size:12px;line-height:1.7}.switch-control{position:relative;flex:0 0 44px;width:44px;height:44px;display:grid;align-items:center}.switch-control input{position:absolute;inset:0;width:44px;height:44px;margin:0;opacity:0;cursor:pointer}.switch-track{pointer-events:none;display:block;height:24px;border-radius:20px;background:#9aa6b4;transition:background .15s}.switch-track::before{content:'';display:block;width:18px;height:18px;margin:3px;border-radius:50%;background:white;box-shadow:0 1px 3px #0f172a30;transition:transform .15s}input:checked+.switch-track{background:var(--accent)}input:checked+.switch-track::before{transform:translateX(20px)}input:focus-visible+.switch-track{outline:3px solid var(--focus);outline-offset:4px}input:disabled+.switch-track{opacity:.5}
</style>

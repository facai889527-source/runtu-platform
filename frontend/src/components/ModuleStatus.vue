<script setup>
defineProps({ status: String })
</script>
<template><span class="badge" :class="{ muted: status === 'disabled' }"><span class="status-dot" aria-hidden="true" />{{ status === 'disabled' ? '已禁用' : '已启用' }}</span></template>

<script setup>
defineProps({ error: Object })
function reload() { window.location.reload() }
</script>

<template>
  <section class="async-view-state" :role="error ? 'alert' : 'status'">
    <p>{{ error ? '页面资源加载失败，请检查连接后重新加载。' : '正在加载页面…' }}</p>
    <button v-if="error" @click="reload">重新加载页面</button>
  </section>
</template>

<style scoped>
.async-view-state { padding: 24px; color: var(--muted); }
.async-view-state[role=alert] { color: var(--danger); }
</style>

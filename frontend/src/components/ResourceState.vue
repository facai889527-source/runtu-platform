<script setup>
import AppIcon from './AppIcon.vue'
defineProps({ pending: Boolean, error: Object, empty: Boolean, emptyText: { type: String, default: '暂无数据。' } })
defineEmits(['retry'])
</script>
<template>
  <div v-if="pending" class="state" role="status"><AppIcon name="refresh" :size="26" /><p>正在读取最新数据…</p></div>
  <div v-else-if="error" class="state error" role="alert"><AppIcon name="alert" :size="28" /><p><strong>{{ error.status ? `读取失败（${error.status}）` : '无法读取数据' }}</strong></p><p>{{ error.message === 'Failed to fetch' ? '网络连接失败，请确认后端已启动。' : error.message }}</p><button @click="$emit('retry')">重新读取</button></div>
  <div v-else-if="empty" class="state"><AppIcon name="module" :size="28" /><p>{{ emptyText }}</p></div>
  <slot v-else />
</template>

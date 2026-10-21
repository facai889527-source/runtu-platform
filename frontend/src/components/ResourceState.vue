<script setup>
defineProps({ pending: Boolean, error: Object, empty: Boolean, emptyText: { type: String, default: '暂无数据。' } })
defineEmits(['retry'])
</script>
<template>
  <div v-if="pending" class="state" role="status">正在读取最新数据…</div>
  <div v-else-if="error" class="state error" role="alert"><strong>{{ error.status ? `读取失败（${error.status}）` : '无法读取数据' }}</strong><p>{{ error.message === 'Failed to fetch' ? '网络连接失败，请确认后端已启动。' : error.message }}</p><button @click="$emit('retry')">重新读取</button></div>
  <div v-else-if="empty" class="state">{{ emptyText }}</div>
  <slot v-else />
</template>

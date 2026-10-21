<script setup>
import { onMounted, onUnmounted } from 'vue'
import { readAccess } from '../api/access.js'
import { useResource } from '../composables/useResource.js'
const access = useResource(readAccess)
const names = { owner: '所有者', admin: '管理员', viewer: '只读成员' }
const permissionNames = { 'platform.read': '平台读取', 'module.read': '模块读取', 'module.manage': '模块管理', 'users.manage': '用户管理', 'audit.read': '审计读取' }
onMounted(() => access.load())
onUnmounted(access.cancel)
</script>
<template>
  <div class="access-summary" aria-label="服务端授权摘要">
    <p v-if="access.pending.value" role="status">正在读取角色与权限…</p>
    <div v-else-if="access.error.value" class="access-unavailable"><p role="status">{{ access.error.value.message }} 当前不展示管理授权。</p><button @click="access.load()">重试权限查询</button></div>
    <template v-else-if="access.data.value">
      <p class="access-role">当前角色：<strong>{{ names[access.data.value.role] }}</strong><span>{{ access.data.value.role }}</span></p>
      <ul aria-label="已授予权限"><li v-for="permission in access.data.value.permissions" :key="permission">{{ permissionNames[permission] }}<span>{{ permission }}</span></li></ul>
      <p class="access-limit">这是服务端确认的授权范围。当前仅开放只读身份查询，管理写入与审计列表尚未开放。</p>
    </template>
  </div>
</template>
<style scoped>
.access-summary { width: 100%; border-top: 1px solid var(--line); padding-top: 16px; }
.access-summary p { margin-bottom: 10px; }
.access-role { display: flex; flex-wrap: wrap; gap: 8px; align-items: baseline; }
.access-role span, li span { color: #526873; font-size: 12px; }
ul { display: flex; flex-wrap: wrap; gap: 8px; }
li { display: flex; flex-direction: column; gap: 4px; border: 1px solid var(--line); background: var(--surface); padding: 10px 12px; border-radius: 8px; }
.access-limit { color: #526873; font-size: 12px; margin-top: 12px; }
.access-unavailable { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
</style>

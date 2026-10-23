<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
import { useResource } from '../composables/useResource.js'
import { readUsers } from '../api/users.js'
import UserCreate from '../components/UserCreate.vue'
import UserRow from '../components/UserRow.vue'
const props = defineProps({ access: Object, selfId: String })
const allowed = computed(() => Boolean(props.access?.data.value?.permissions.includes('users.manage')))
const users = useResource(readUsers), after = ref(null), previous = ref([])
function load() { users.load(after.value) }
function first() { after.value = null; previous.value = []; load() }
function next() { const cursor = users.data.value?.next_after_username; if (cursor != null) { previous.value.push(after.value); after.value = cursor; load() } }
function back() { if (previous.value.length) { after.value = previous.value.pop(); load() } }
watch(allowed, () => { users.cancel(); users.data.value = null; users.error.value = null; after.value = null; previous.value = []; if (allowed.value) load() }, { immediate: true })
onUnmounted(users.cancel)
</script>
<template>
  <div class="users-page">
    <p v-if="access?.pending.value" role="status">正在确认用户管理权限…</p>
    <div v-else-if="access?.error.value" class="panel users-list" role="status">用户管理权限暂无法确认。<button @click="access.load()">重试权限查询</button></div>
    <p v-else-if="!allowed" class="panel users-list" role="status">当前身份没有用户管理权限。</p>
    <template v-else>
      <section class="panel users-list" aria-labelledby="users-list-title"><div class="section-heading"><div><h2 id="users-list-title">账户列表</h2><p class="subtle">按用户名排序，每页20位。角色或启停变更将撤销该用户已有会话。</p></div><button type="button" :disabled="users.pending.value" @click="first">刷新列表</button></div>
        <details class="create-disclosure"><summary>创建账户<span class="subtle">为新成员设置初始角色</span></summary><UserCreate @created="first" /></details>
        <p v-if="users.pending.value" role="status">正在加载用户…</p>
        <div v-else-if="users.error.value" role="alert"><p>{{ users.error.value.message }}</p><button type="button" @click="load">重试加载</button></div>
        <template v-else-if="users.data.value"><p v-if="!users.data.value.items.length" class="subtle">此页暂无用户。</p><ul v-else class="user-items"><UserRow v-for="user in users.data.value.items" :key="user.id" :user="user" :self-id="selfId" @updated="load" /></ul></template>
        <nav class="user-pagination" aria-label="用户分页"><button type="button" :disabled="users.pending.value || !previous.length" @click="back">上一页</button><button type="button" :disabled="users.pending.value || users.data.value?.next_after_username == null" @click="next">下一页</button></nav>
      </section>
    </template>
  </div>
</template>
<style scoped>
.users-page { display: grid; gap: 20px; } .create-disclosure { margin-bottom: 20px; border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 0 16px; } .create-disclosure summary { min-height: 52px; cursor: pointer; padding: 14px 0; font-weight: 600; } .create-disclosure summary span { margin-left: 16px; font-size: 12px; font-weight: 400; } .users-list { padding: 24px; min-width: 0; } .section-heading { flex-wrap: wrap; gap: 16px; align-items: center; } h2 { margin: 0; } .user-items { list-style: none; padding: 0; margin: 0; } .user-pagination { display: flex; justify-content: flex-end; gap: 12px; } button { min-height: 44px; } @media(max-width:760px) { .users-list { padding: 20px; } }
</style>

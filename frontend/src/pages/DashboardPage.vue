<script setup>
import { computed } from 'vue'
import ResourceState from '../components/ResourceState.vue'
import MyModules from '../components/MyModules.vue'
import RouteLink from '../components/RouteLink.vue'
import AppIcon from '../components/AppIcon.vue'
import { databaseLabels, moduleCounts } from '../utils/modules.js'
import { modulePath } from '../navigation/history.js'
const props = defineProps({ health: Object, modules: Object, userId: String, showDiagnostics: Boolean })
const counts = computed(() => props.modules.data.value ? moduleCounts(props.modules.data.value) : null)
const publicTools = computed(() => props.modules.data.value?.filter(item => item.access_mode !== 'assigned' && item.status === 'enabled') || [])
</script>
<template>
  <MyModules :user-id="userId" />
  <section v-if="publicTools.length" class="panel public-tools" aria-labelledby="public-tools-title">
    <div class="section-heading"><div><h2 id="public-tools-title">公开工具</h2><p class="section-description">平台提供的公开演示入口。</p></div></div>
    <ul class="tool-grid"><li v-for="item in publicTools" :key="item.id"><RouteLink class="tool-link overview-name" :to="modulePath(item.id)"><span class="module-avatar"><AppIcon name="module" /></span><span><strong>{{ item.name }}</strong><small>{{ item.description }}</small></span><AppIcon name="right" :size="16" /></RouteLink></li></ul>
  </section>
  <details v-if="showDiagnostics" class="panel system-status"><summary>平台运行状态<span class="subtle">管理员诊断</span></summary>
    <ResourceState :pending="health.pending.value" :error="health.error.value" @retry="health.load()"><dl v-if="health.data.value" class="diagnostic-grid"><div><dt>后端服务</dt><dd>{{ health.data.value.status === 'ok' ? '运行正常' : '服务降级' }}</dd></div><div><dt>数据库</dt><dd>{{ databaseLabels[health.data.value.database] }}</dd></div><div v-if="counts"><dt>模块清单</dt><dd>{{ counts.enabled }} 已启用 / {{ counts.total }} 已注册</dd></div></dl></ResourceState>
  </details>
</template>

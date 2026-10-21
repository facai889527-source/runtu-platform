<script setup>
import { computed } from 'vue'
import ResourceState from '../components/ResourceState.vue'
import ModuleStatus from '../components/ModuleStatus.vue'
import RouteLink from '../components/RouteLink.vue'
import { databaseLabels, moduleCounts } from '../utils/modules.js'
const props = defineProps({ health: Object, modules: Object })
const counts = computed(() => props.modules.data.value ? moduleCounts(props.modules.data.value) : null)
</script>
<template>
  <p class="lead">平台运行状态与模块，一目了然。</p>
  <section class="panel health-panel" aria-labelledby="health-title"><div class="section-heading"><h2 id="health-title">平台健康</h2><span class="subtle">当前检查结果</span></div>
    <ResourceState :pending="health.pending.value" :error="health.error.value" @retry="health.load()">
      <div v-if="health.data.value" class="health-content"><span class="health-symbol" aria-hidden="true">{{ health.data.value.status === 'ok' ? '✓' : '!' }}</span><div><h3>{{ health.data.value.status === 'ok' ? '后端运行正常' : '后端已连接，服务降级' }}</h3><p :class="{ error: health.data.value.database === 'unavailable' }">{{ databaseLabels[health.data.value.database] }}</p></div></div>
    </ResourceState>
  </section>
  <section aria-label="模块统计" class="statistics"><div v-for="(label, key) in { total: '已注册模块', enabled: '已启用模块', disabled: '已禁用模块' }" :key="key" class="stat"><span>{{ label }}</span><strong>{{ counts ? counts[key] : '—' }}</strong><small v-if="!counts">{{ modules.pending.value ? '读取中' : '暂不可用' }}</small></div></section>
  <section class="panel" aria-labelledby="overview-title"><div class="section-heading"><h2 id="overview-title">模块概览</h2><RouteLink class="text-button" to="/modules">查看全部模块</RouteLink></div>
    <ResourceState :pending="modules.pending.value" :error="modules.error.value" :empty="modules.data.value?.length === 0" empty-text="暂无已注册模块。后续接入的模块将在这里显示。" @retry="modules.load()">
      <ul class="overview-list"><li v-for="item in modules.data.value?.slice(0, 5)" :key="item.id"><div><strong>{{ item.name }}</strong><p>{{ item.description }}</p></div><ModuleStatus :status="item.status" /></li></ul>
    </ResourceState>
  </section>
</template>

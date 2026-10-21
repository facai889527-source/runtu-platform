<script setup>
import { computed } from 'vue'
import ResourceState from '../components/ResourceState.vue'
import ModuleStatus from '../components/ModuleStatus.vue'
import RouteLink from '../components/RouteLink.vue'
import AppIcon from '../components/AppIcon.vue'
import { databaseLabels, moduleCounts } from '../utils/modules.js'
import { modulePath } from '../navigation/history.js'
import MyModules from '../components/MyModules.vue'
const props = defineProps({ health: Object, modules: Object, userId: String })
const counts = computed(() => props.modules.data.value ? moduleCounts(props.modules.data.value) : null)
const metrics = [
  { key: 'total', label: '已注册模块', icon: 'module', note: '平台已接入的模块' },
  { key: 'enabled', label: '已启用模块', icon: 'power', note: '按注册清单启用' },
  { key: 'disabled', label: '已禁用模块', icon: 'pause', note: '保留信息，仅供查看' },
]
</script>

<template>
  <section class="panel health-panel" aria-labelledby="health-title">
    <div class="section-heading compact-heading"><h2 id="health-title">平台健康</h2></div>
    <ResourceState :pending="health.pending.value" :error="health.error.value" @retry="health.load()">
      <div v-if="health.data.value" class="health-summary">
        <div class="health-content">
          <span class="health-symbol" :class="{ warning: health.data.value.status !== 'ok' }"><AppIcon :name="health.data.value.status === 'ok' ? 'check' : 'alert'" :size="22" /></span>
          <div><h3>{{ health.data.value.status === 'ok' ? '后端运行正常' : '后端已连接，服务降级' }}</h3></div>
        </div>
        <div class="database-summary" :class="{ warning: health.data.value.database === 'not_configured', danger: health.data.value.database === 'unavailable' }">
          <AppIcon name="database" :size="19" /><div><span class="database-label">数据库状态</span><p>{{ databaseLabels[health.data.value.database] }}</p></div>
        </div>
      </div>
    </ResourceState>
  </section>
  <section aria-label="模块统计" class="statistics">
    <article v-for="metric in metrics" :key="metric.key" class="stat" :class="`stat-${metric.key}`">
      <div class="stat-top"><span>{{ metric.label }}</span><span class="stat-icon"><AppIcon :name="metric.icon" :size="19" /></span></div>
      <strong>{{ counts ? counts[metric.key] : '—' }}</strong>
      <p>{{ counts ? metric.note : modules.pending.value ? '正在读取模块' : '数据暂不可用' }}</p>
    </article>
  </section>
  <section class="panel overview-panel" aria-labelledby="overview-title">
    <div class="section-heading"><div class="heading-with-count"><h2 id="overview-title">模块概览</h2><span v-if="counts" class="count-badge">{{ counts.total }}</span></div><RouteLink class="text-button" to="/modules">查看全部模块<AppIcon name="right" :size="16" /></RouteLink></div>
    <ResourceState :pending="modules.pending.value" :error="modules.error.value" :empty="modules.data.value?.length === 0" empty-text="暂无已注册模块。后续接入的模块将在这里显示。" @retry="modules.load()">
      <ul class="overview-list">
        <li v-for="item in modules.data.value?.slice(0, 5)" :key="item.id">
          <span class="module-avatar"><AppIcon name="module" :size="22" /></span>
          <div class="overview-copy"><RouteLink class="overview-name" :to="modulePath(item.id)">{{ item.name }}</RouteLink><p>{{ item.description }}</p><span class="module-id">{{ item.id }}<span class="version">v{{ item.version }}</span></span></div>
          <div class="overview-action"><ModuleStatus :status="item.status" /><RouteLink class="icon-link" :to="modulePath(item.id)" :aria-label="`查看${item.name}详情`"><AppIcon name="right" :size="18" /></RouteLink></div>
        </li>
      </ul>
    </ResourceState>
    <div v-if="counts && counts.total > 5" class="panel-footnote"><AppIcon name="info" :size="15" /><span>展示前 5 个模块，完整目录共 {{ counts.total }} 个。</span></div>
  </section>
  <MyModules :user-id="userId" />
</template>

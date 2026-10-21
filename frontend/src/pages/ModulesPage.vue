<script setup>
import { ref, computed } from 'vue'
import ResourceState from '../components/ResourceState.vue'
import ModuleStatus from '../components/ModuleStatus.vue'
import ModuleDetail from '../components/ModuleDetail.vue'
import RouteLink from '../components/RouteLink.vue'
import AppIcon from '../components/AppIcon.vue'
import { modulePath } from '../navigation/history.js'
import { filterModules } from '../utils/modules.js'
const props = defineProps({ modules: Object, moduleId: { type: String, default: null } })
const query = ref(''), status = ref('all')
const filtered = computed(() => filterModules(props.modules.data.value || [], query.value, status.value))
function clear() { query.value = ''; status.value = 'all' }
</script>

<template>
  <ModuleDetail v-if="moduleId" :module-id="moduleId" />
  <template v-else>
    <p class="lead">每一项能力，都有清晰的位置。</p>
    <section class="panel directory-panel" aria-labelledby="directory-title">
      <div class="section-heading"><div><h2 id="directory-title">模块目录</h2><p class="section-description">查找已接入模块，了解状态与公开配置。</p></div><span class="readonly-label"><AppIcon name="lock" :size="14" />只读</span></div>
      <div class="filters">
        <label class="search-label">搜索模块<span class="search-field"><AppIcon name="search" :size="18" /><input v-model="query" type="search" placeholder="搜索名称、标识或能力…" /></span></label>
        <label>模块状态<select v-model="status"><option value="all">全部状态</option><option value="enabled">已启用</option><option value="disabled">已禁用</option></select></label>
        <button class="reset-button" @click="clear">重置筛选</button>
      </div>
      <ResourceState :pending="modules.pending.value" :error="modules.error.value" :empty="modules.data.value?.length === 0" empty-text="暂无已注册模块。" @retry="modules.load()">
        <div class="directory-summary"><p class="result-count" role="status">找到 <strong>{{ filtered.length }}</strong> 个模块</p><span class="subtle">点击模块名称查看详情</span></div>
        <div v-if="!filtered.length" class="state"><AppIcon name="search" :size="28" /><p>没有匹配的模块，请调整搜索条件。</p><button @click="clear">清除筛选</button></div>
        <ul v-else class="module-list">
          <li v-for="item in filtered" :key="item.id" :class="{ 'module-disabled': item.status === 'disabled' }">
            <div class="module-card-top"><span class="module-avatar"><AppIcon name="module" :size="24" /></span><ModuleStatus :status="item.status" /></div>
            <div class="module-header"><h3><RouteLink class="module-link" :to="modulePath(item.id)">{{ item.name }}</RouteLink></h3><span class="module-id">{{ item.id }}<span class="version">v{{ item.version }}</span></span></div>
            <p class="module-description">{{ item.description || '此模块尚未提供描述。' }}</p>
            <div class="module-meta"><span class="category-tag">{{ item.category || '未分类' }}</span><span>{{ item.capabilities?.length ? item.capabilities.join('、') : '未声明能力' }}</span><RouteLink class="icon-link" :to="modulePath(item.id)" :aria-label="`查看${item.name}详情`"><AppIcon name="arrow" :size="18" /></RouteLink></div>
            <p v-if="item.status === 'disabled'" class="disabled-note">业务路由不可用，仍可查看公开配置。</p>
          </li>
        </ul>
      </ResourceState>
    </section>
  </template>
</template>

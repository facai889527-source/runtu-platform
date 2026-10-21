<script setup>
import { ref, computed } from 'vue'
import ResourceState from '../components/ResourceState.vue'
import ModuleStatus from '../components/ModuleStatus.vue'
import ModuleDetail from '../components/ModuleDetail.vue'
import RouteLink from '../components/RouteLink.vue'
import AppIcon from '../components/AppIcon.vue'
import { modulePath } from '../navigation/history.js'
import { filterModules } from '../utils/modules.js'
const props = defineProps({ modules: Object, access: Object, moduleId: { type: String, default: null } })
defineEmits(['changed'])
const query = ref(''), status = ref('all')
const filtered = computed(() => filterModules(props.modules.data.value || [], query.value, status.value))
function clear() { query.value = ''; status.value = 'all' }
</script>

<template>
  <ModuleDetail v-if="moduleId" :module-id="moduleId" :access="access" @changed="$emit('changed')" />
  <template v-else>
    <section class="panel directory-panel" aria-labelledby="directory-title">
      <div class="section-heading"><div><h2 id="directory-title">模块目录</h2><p class="section-description">查看运行状态，在详情中管理启用状态与公开配置。</p></div></div>
      <div class="filters">
        <label class="search-label">搜索模块<span class="search-field"><AppIcon name="search" :size="18" /><input v-model="query" type="search" placeholder="名称、标识或能力" aria-describedby="directory-hint" /></span></label>
        <label>模块状态<select v-model="status"><option value="all">全部状态</option><option value="enabled">已启用</option><option value="disabled">已禁用</option></select></label>
        <button class="reset-button" @click="clear">重置筛选</button>
      </div>
      <p id="directory-hint" class="filter-hint">搜索与状态筛选仅作用于当前模块目录。</p>
      <ResourceState :pending="modules.pending.value" :error="modules.error.value" :empty="modules.data.value?.length === 0" empty-text="暂无已注册模块。" @retry="modules.load()">
        <div class="directory-summary"><p class="result-count" role="status" aria-live="polite">找到 <strong>{{ filtered.length }}</strong> 个模块<span v-if="query.trim() || status !== 'all'" class="filter-applied"> · 已应用筛选</span></p><span class="subtle">选择模块查看详情</span></div>
        <div v-if="!filtered.length" class="state"><AppIcon name="search" :size="28" /><p>没有匹配的模块，请调整搜索条件。</p><button @click="clear">清除筛选</button></div>
        <ul v-else class="module-list" :class="{ 'single-module': filtered.length === 1 }">
          <li v-for="item in filtered" :key="item.id" :class="{ 'module-disabled': item.status === 'disabled' }">
            <div class="module-card-top"><span class="module-avatar"><AppIcon name="module" :size="24" /></span><ModuleStatus :status="item.status" /></div>
            <div class="module-header"><h3><RouteLink class="module-link" :to="modulePath(item.id)" :title="item.name || item.id">{{ item.name || item.id }}</RouteLink></h3><span class="module-id">{{ item.id }}<span class="version" :title="item.version">v{{ item.version || '未提供' }}</span></span></div>
            <p class="module-description">{{ item.description || '此模块尚未提供描述。' }}</p>
            <div class="module-meta"><span class="category-tag">{{ item.category || '未分类' }}</span><span class="capability-summary">{{ item.capabilities?.length ? item.capabilities.join('、') : '未声明能力' }}</span><span class="card-arrow" aria-hidden="true"><AppIcon name="arrow" :size="18" /></span></div>
            <p v-if="item.status === 'disabled'" class="disabled-note">业务路由不可用，仍可查看公开配置。</p>
          </li>
        </ul>
      </ResourceState>
    </section>
  </template>
</template>

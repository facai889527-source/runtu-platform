<script setup>
import { ref, computed } from 'vue'
import ResourceState from '../components/ResourceState.vue'
import ModuleStatus from '../components/ModuleStatus.vue'
import ModuleDetail from '../components/ModuleDetail.vue'
import RouteLink from '../components/RouteLink.vue'
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
    <p class="lead">浏览平台已注册的能力与公开配置。</p>
    <section class="panel" aria-labelledby="directory-title"><div class="section-heading"><h2 id="directory-title">模块目录</h2><span class="subtle">只读</span></div>
      <div class="filters"><label>搜索模块<input v-model="query" type="search" placeholder="名称、标识或能力" /></label><label>模块状态<select v-model="status"><option value="all">全部状态</option><option value="enabled">已启用</option><option value="disabled">已禁用</option></select></label><button @click="clear">重置筛选</button></div>
      <ResourceState :pending="modules.pending.value" :error="modules.error.value" :empty="modules.data.value?.length === 0" empty-text="暂无已注册模块。" @retry="modules.load()">
        <p class="result-count" role="status">找到 {{ filtered.length }} 个模块</p>
        <div v-if="!filtered.length" class="state">没有匹配的模块，请调整搜索条件。<button @click="clear">清除筛选</button></div>
        <ul v-else class="module-list"><li v-for="item in filtered" :key="item.id"><div class="module-header"><div><h3><RouteLink class="module-link" :to="modulePath(item.id)">{{ item.name }}</RouteLink></h3><span class="subtle">{{ item.id }} / v{{ item.version }}</span></div><ModuleStatus :status="item.status" /></div><p>{{ item.description }}</p><div class="module-meta"><span>{{ item.category || '未分类' }}</span><span>{{ item.capabilities?.length ? item.capabilities.join('、') : '未声明能力' }}</span></div><p v-if="item.status === 'disabled'" class="disabled-note">业务路由不可用，仍可查看公开配置。</p></li></ul>
      </ResourceState>
    </section>
  </template>
</template>

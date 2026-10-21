<script setup>
import { watch, onUnmounted } from 'vue'
import { useResource } from '../composables/useResource.js'
import { readModule } from '../api/client.js'
import ResourceState from './ResourceState.vue'
import ModuleStatus from './ModuleStatus.vue'
import RouteLink from './RouteLink.vue'
import AppIcon from './AppIcon.vue'
const props = defineProps({ moduleId: { type: String, required: true } })
const detail = useResource(readModule)
watch(() => props.moduleId, (id) => detail.load(id), { immediate: true })
onUnmounted(detail.cancel)
</script>

<template>
  <RouteLink class="back-button" to="/modules"><AppIcon name="back" :size="17" />返回模块目录</RouteLink>
  <ResourceState :pending="detail.pending.value" :error="detail.error.value" @retry="detail.load(moduleId)">
    <template v-if="detail.data.value">
      <section class="panel detail-identity" aria-label="模块摘要">
        <span class="module-avatar large-avatar"><AppIcon name="module" :size="28" /></span>
        <div class="identity-copy"><div class="identity-title"><h2>{{ detail.data.value.name || detail.data.value.id }}</h2><ModuleStatus :status="detail.data.value.status" /></div><p>{{ detail.data.value.description || '此模块尚未提供描述。' }}</p><span class="module-id">{{ detail.data.value.id }}<span class="version">v{{ detail.data.value.version || '未提供' }}</span></span></div>
      </section>
      <p v-if="detail.data.value.status === 'disabled'" class="disabled-note">此模块已禁用，业务路由不可用。以下信息仅供查看。</p>
      <div class="detail-columns">
        <section class="panel information-panel" aria-labelledby="information-title">
          <div class="section-heading"><div class="icon-heading"><AppIcon name="module" /><h2 id="information-title">模块信息</h2></div></div>
          <dl class="info-grid"><div><dt>模块标识</dt><dd>{{ detail.data.value.id }}</dd></div><div><dt>版本</dt><dd>{{ detail.data.value.version || '未提供' }}</dd></div><div><dt>分类</dt><dd>{{ detail.data.value.category || '未分类' }}</dd></div><div><dt>运行状态</dt><dd><ModuleStatus :status="detail.data.value.status" /></dd></div><div class="info-wide"><dt>能力声明</dt><dd><span v-for="capability in detail.data.value.capabilities" :key="capability" class="capability-tag">{{ capability }}</span><span v-if="!detail.data.value.capabilities?.length" class="subtle">未声明能力</span></dd></div></dl>
        </section>
        <section class="panel configuration-panel" aria-labelledby="config-title">
          <div class="section-heading"><div class="icon-heading"><AppIcon name="settings" /><h2 id="config-title">公开配置</h2></div><span class="readonly-label">只读</span></div>
          <div class="config-entry"><div><h3>导航展示偏好</h3><p>模块声明的导航可见性</p></div><span class="config-value">{{ detail.data.value.public_config.show_in_navigation ? '显示' : '隐藏' }}</span></div>
          <div class="config-entry"><div><h3>刷新间隔偏好</h3><p>模块声明的数据刷新间隔</p></div><span class="config-value">{{ detail.data.value.public_config.refresh_interval_seconds == null ? '未设置' : `${detail.data.value.public_config.refresh_interval_seconds} 秒` }}</span></div>
          <div class="config-note"><AppIcon name="info" :size="17" /><p>配置编辑功能尚未开放，与账户角色权限无关。此处偏好不会自动刷新或隐藏模块。</p></div>
        </section>
      </div>
    </template>
  </ResourceState>
</template>

<script setup>
import { watch, onUnmounted, nextTick, useTemplateRef } from 'vue'
import { useResource } from '../composables/useResource.js'
import { readModule } from '../api/client.js'
import ResourceState from './ResourceState.vue'
import ModuleStatus from './ModuleStatus.vue'
const props = defineProps({ moduleId: { type: String, required: true } })
defineEmits(['back'])
const detail = useResource(readModule)
const heading = useTemplateRef('heading')
watch(() => props.moduleId, async (id) => { detail.load(id); await nextTick(); heading.value?.focus() }, { immediate: true })
onUnmounted(detail.cancel)
</script>
<template>
  <button class="back-button" @click="$emit('back')">返回模块目录</button>
  <section class="panel"><h2 ref="heading" tabindex="-1">模块详情</h2>
    <ResourceState :pending="detail.pending.value" :error="detail.error.value" @retry="detail.load(moduleId)">
      <template v-if="detail.data.value"><div class="detail-heading"><h3>{{ detail.data.value.name }}</h3><ModuleStatus :status="detail.data.value.status" /></div><p>{{ detail.data.value.description }}</p><p v-if="detail.data.value.status === 'disabled'" class="disabled-note">此模块已禁用，业务路由不可用。以下信息仅供查看。</p>
        <dl class="details"><dt>模块标识</dt><dd>{{ detail.data.value.id }}</dd><dt>版本</dt><dd>{{ detail.data.value.version }}</dd><dt>分类</dt><dd>{{ detail.data.value.category || '未分类' }}</dd><dt>能力声明</dt><dd>{{ detail.data.value.capabilities?.join('、') || '未声明能力' }}</dd></dl>
        <h3>公开配置</h3><dl class="details"><dt>导航展示偏好</dt><dd>{{ detail.data.value.public_config.show_in_navigation ? '显示' : '隐藏' }}</dd><dt>刷新间隔偏好</dt><dd>{{ detail.data.value.public_config.refresh_interval_seconds == null ? '未设置' : `${detail.data.value.public_config.refresh_interval_seconds} 秒` }}</dd></dl><p class="subtle">仅展示服务端公开偏好，不代表本页面已开启自动刷新或隐藏模块。管理配置将在认证授权完成后开放。</p>
      </template>
    </ResourceState>
  </section>
</template>

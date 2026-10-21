<script setup>
import { onMounted, ref } from 'vue'

const platform = ref('Runtu Platform')
const health = ref('正在连接')
const modules = ref([])
const error = ref('')
const loading = ref(false)

async function refresh() {
  loading.value = true
  error.value = ''
  modules.value = []
  health.value = '正在连接'
  try {
    const responses = await Promise.all([
      fetch('/api/health', { signal: AbortSignal.timeout(8000) }),
      fetch('/api/modules', { signal: AbortSignal.timeout(8000) }),
    ])
    if (responses.some((response) => !response.ok)) throw new Error('API response failed')
    const [status, registered] = await Promise.all(responses.map((response) => response.json()))
    if (status.status !== 'ok' || !Array.isArray(registered)) throw new Error('Invalid API response')
    platform.value = status.platform
    health.value = '运行正常'
    modules.value = registered
  } catch {
    health.value = '连接失败'
    error.value = '无法读取平台状态，请确认后端已启动后重试。'
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <main>
    <header>
      <p class="eyebrow">模块化管理平台</p>
      <h1>{{ platform }}</h1>
      <p>从一个清晰的核心开始，逐步连接所需的管理模块。</p>
    </header>
    <section aria-labelledby="status-title">
      <div class="section-heading">
        <h2 id="status-title">平台状态</h2>
        <button :disabled="loading" @click="refresh">{{ loading ? '连接中…' : '刷新状态' }}</button>
      </div>
      <p role="status">后端：{{ health }}</p>
      <p v-if="error" role="alert" class="error">{{ error }}</p>
    </section>
    <section aria-labelledby="modules-title">
      <h2 id="modules-title">已注册模块</h2>
      <ul v-if="modules.length">
        <li v-for="module in modules" :key="module.id">
          <h3>{{ module.name }} <small>v{{ module.version }}</small></h3>
          <p>{{ module.description }}</p>
        </li>
      </ul>
      <p v-else>{{ loading ? '正在读取模块…' : error ? '模块列表暂不可用。' : '暂无已注册模块。' }}</p>
    </section>
  </main>
</template>

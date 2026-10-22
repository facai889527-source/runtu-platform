import { shallowRef } from 'vue'

export function useResource(reader, { retainData = false } = {}) {
  const data = shallowRef(null), error = shallowRef(null), pending = shallowRef(false)
  let generation = 0, controller
  function cancel() { generation++; controller?.abort(); pending.value = false }
  async function load(...args) {
    cancel()
    const current = generation
    controller = new AbortController()
    const active = controller
    const timer = setTimeout(() => active.abort(new Error('请求超时，请重试。')), 8000)
    pending.value = true; error.value = null
    if (!retainData) data.value = null
    try {
      const result = await reader(...args, active.signal)
      if (current === generation) data.value = result
    } catch (cause) {
      if (current === generation) { data.value = null; error.value = cause instanceof Error ? cause : new Error('网络连接失败。') }
    } finally {
      clearTimeout(timer)
      if (current === generation) pending.value = false
    }
  }
  return { data, error, pending, load, cancel }
}

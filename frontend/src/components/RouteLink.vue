<script setup>
import { useNavigation } from '../navigation/context.js'

const props = defineProps({ to: { type: String, required: true } })
const emit = defineEmits(['navigate'])
const { navigate } = useNavigation()
function follow(event) {
  // Preserve native copy/open-in-new-tab and modified-click behavior.
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  navigate(props.to)
  emit('navigate')
}
</script>

<template><a :href="to" @click="follow"><slot /></a></template>

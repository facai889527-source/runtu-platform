import { inject, provide, shallowRef, readonly, onUnmounted } from 'vue'
import { createNavigation } from './history.js'

const navigationKey = Symbol('navigation')

export function provideNavigation() {
  const navigation = createNavigation(window)
  const route = shallowRef(navigation.current())
  const unsubscribe = navigation.subscribe((value) => { route.value = value })
  const context = { route: readonly(route), navigate: navigation.navigate }
  provide(navigationKey, context)
  onUnmounted(() => { unsubscribe(); navigation.dispose() })
  return context
}

export function useNavigation() {
  const navigation = inject(navigationKey)
  if (!navigation) throw new Error('Navigation provider is required')
  return navigation
}

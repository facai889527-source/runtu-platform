import { defineAsyncComponent } from 'vue'
import AsyncViewState from './AsyncViewState.vue'

// Keep the authentication entry eager; load other views only when rendered.
export function asyncView(loader) {
  return defineAsyncComponent({
    loader,
    loadingComponent: AsyncViewState,
    errorComponent: AsyncViewState,
    delay: 200,
    timeout: 15000,
  })
}

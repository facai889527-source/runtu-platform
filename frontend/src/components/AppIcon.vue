<script setup>
defineProps({ name: { type: String, default: 'module' }, size: { type: [Number, String], default: 20 } })
const paths = {
  dashboard: ['M3 3h7v7H3z', 'M14 3h7v4h-7z', 'M14 11h7v10h-7z', 'M3 14h7v7H3z'],
  module: ['m12 3 9 5-9 5-9-5 9-5Z', 'm3 12 9 5 9-5', 'm3 16 9 5 9-5'],
  settings: ['M4 7h16M4 17h16', 'M9 4v6M15 14v6'],
  menu: ['M4 6h16M4 12h16M4 18h16'],
  close: ['m6 6 12 12M6 18 18 6'],
  left: ['m14 6-6 6 6 6'],
  right: ['m10 6 6 6-6 6'],
  arrow: ['M4 12h16m-6-6 6 6-6 6'],
  back: ['M20 12H4m6-6-6 6 6 6'],
  refresh: ['M20 7v5h-5', 'M4 17v-5h5', 'M6.1 6.1A8 8 0 0 1 20 12M4 12a8 8 0 0 0 13.9 5.9'],
  check: ['m6 12 4 4 8-8'],
  database: ['M20 6c0 2-3.6 3-8 3S4 8 4 6s3.6-3 8-3 8 1 8 3Z', 'M4 6v6c0 2 3.6 3 8 3s8-1 8-3V6', 'M4 12v6c0 2 3.6 3 8 3s8-1 8-3v-6'],
  alert: ['M12 3 2 21h20L12 3Z', 'M12 9v5m0 3v.1'],
  search: ['M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z', 'm15 15 6 6'],
  power: ['M12 3v9', 'M6.4 5.7a8 8 0 1 0 11.2 0'],
  pause: ['M8 5v14M16 5v14'],
  lock: ['M6 10h12v11H6z', 'M8 10V7a4 4 0 0 1 8 0v3', 'M12 14v3'],
  bell: ['M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9', 'M10 21h4'],
  info: ['M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z', 'M12 11v6m0-10v.1'],
}
</script>

<template>
  <svg class="app-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
    <path v-for="(path, index) in (paths[name] || paths.module)" :key="index" :d="path" />
  </svg>
</template>

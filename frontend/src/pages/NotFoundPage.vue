<script setup>
import RouteLink from '../components/RouteLink.vue'
</script>

<template>
  <section class="panel settings" aria-labelledby="not-found-title">
    <h2 id="not-found-title">404 · 找不到这个页面</h2>
    <p>请检查地址，或返回仪表盘继续浏览。</p>
    <RouteLink class="button-link" to="/">返回仪表盘</RouteLink>
  </section>
</template>

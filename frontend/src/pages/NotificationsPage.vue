<script setup>
import NotificationSettings from '../components/NotificationSettings.vue'
</script>

<template>
  <section class="notifications-page" aria-labelledby="notifications-title">
    <div class="notification-heading"><h2 id="notifications-title">我的消息</h2><p>连接自己的 Telegram，独立选择接收的通知。</p></div>
    <NotificationSettings />
  </section>
</template>

<style scoped>
.notifications-page{max-width:860px}.notification-heading{margin-bottom:28px}.notification-heading h2{font-size:22px;letter-spacing:-.02em;margin:0 0 8px}.notification-heading p{color:var(--muted);font-size:13px;line-height:1.8;margin:0}
</style>

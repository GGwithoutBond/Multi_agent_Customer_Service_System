<script setup lang="ts">
import { computed } from 'vue'
import { RouterView } from 'vue-router'
import {
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  NNotificationProvider,
  createDiscreteApi,
  zhCN,
  dateZhCN
} from 'naive-ui'
import { buildNaiveThemeOverrides } from '@/theme/tokens'

const themeOverrides = computed(() => buildNaiveThemeOverrides())

// Create discrete API for use outside of setup (e.g., in axios interceptors)
const { message } = createDiscreteApi(['message'])
window.$message = message
</script>

<template>
  <n-config-provider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <RouterView />
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style>
html, body, #root {
  height: 100%;
  margin: 0;
  padding: 0;
  font-family: 'Inter', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}
</style>

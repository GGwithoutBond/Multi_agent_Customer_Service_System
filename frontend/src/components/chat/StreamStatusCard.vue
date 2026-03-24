<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { AlertCircleOutline, RefreshOutline, WifiOutline } from '@vicons/ionicons5'

withDefaults(
  defineProps<{
    state: 'idle' | 'streaming' | 'stopped' | 'error' | 'offline'
    reason?: string
    canRetry?: boolean
  }>(),
  {
    reason: '',
    canRetry: false,
  },
)

const emit = defineEmits<{
  retry: []
  recover: []
  dismiss: []
}>()
</script>

<template>
  <div class="stream-status-card">
    <div class="status-leading">
      <n-icon :size="18" class="status-icon">
        <WifiOutline v-if="state === 'offline'" />
        <AlertCircleOutline v-else />
      </n-icon>
      <div class="status-text">
        <div class="title">
          {{ state === 'offline' ? '网络已断开' : state === 'error' ? '响应中断' : '生成已停止' }}
        </div>
        <div class="desc">{{ reason || '你可以重试上一条，或继续当前会话。' }}</div>
      </div>
    </div>
    <div class="status-actions">
      <button v-if="canRetry" type="button" class="ds-pill-btn ds-pill-btn-primary" @click="emit('retry')">
        <n-icon :size="14">
          <RefreshOutline />
        </n-icon>
        重试上一条
      </button>
      <button type="button" class="ds-pill-btn ds-pill-btn-subtle" @click="emit('recover')">继续当前会话</button>
      <button type="button" class="dismiss-btn" @click="emit('dismiss')">关闭</button>
    </div>
  </div>
</template>

<style scoped>
.stream-status-card {
  margin-top: 10px;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid var(--ds-border);
  background: linear-gradient(180deg, #ffffff, #f6f9ff);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.status-leading {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-icon {
  color: var(--ds-warning);
}

.status-text .title {
  font-size: 13px;
  font-weight: 700;
  color: var(--ds-text-primary);
}

.status-text .desc {
  font-size: 12px;
  color: var(--ds-text-tertiary);
  margin-top: 3px;
}

.status-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dismiss-btn {
  border: none;
  background: transparent;
  color: var(--ds-text-tertiary);
  font-size: 12px;
  cursor: pointer;
}

.dismiss-btn:hover {
  color: var(--ds-text-primary);
}

@media (max-width: 768px) {
  .stream-status-card {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>

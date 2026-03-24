<script setup lang="ts">
import { computed, h } from 'vue'
import { NIcon } from 'naive-ui'
import type { UIStateType } from '@/types/ui-state'
import {
  AlertCircleOutline,
  CloudOfflineOutline,
  RefreshOutline,
  SearchOutline,
  TimeOutline,
} from '@vicons/ionicons5'

const props = withDefaults(
  defineProps<{
    type: UIStateType
    title: string
    description?: string
    actionText?: string
    compact?: boolean
  }>(),
  {
    description: '',
    actionText: '',
    compact: false,
  },
)

const emit = defineEmits<{
  action: []
}>()

const icon = computed(() => {
  if (props.type === 'loading') return TimeOutline
  if (props.type === 'empty') return SearchOutline
  if (props.type === 'offline') return CloudOfflineOutline
  return AlertCircleOutline
})

const iconClass = computed(() => {
  if (props.type === 'error') return 'error'
  if (props.type === 'offline') return 'offline'
  if (props.type === 'empty') return 'empty'
  return 'loading'
})

const shouldSpin = computed(() => props.type === 'loading')
</script>

<template>
  <section class="ui-state" :class="{ compact }" role="status" aria-live="polite">
    <div class="ui-state-icon-wrap" :class="iconClass">
      <n-icon :size="24" :class="{ spinning: shouldSpin }">
        <component :is="icon" />
      </n-icon>
    </div>
    <h3 class="ui-state-title">{{ title }}</h3>
    <p v-if="description" class="ui-state-description">{{ description }}</p>
    <button v-if="actionText" type="button" class="ui-state-action ds-pill-btn ds-pill-btn-primary" @click="emit('action')">
      <n-icon :size="14">
        <RefreshOutline />
      </n-icon>
      <span>{{ actionText }}</span>
    </button>
  </section>
</template>

<style scoped>
.ui-state {
  width: 100%;
  border-radius: var(--ds-radius-lg);
  border: 1px solid var(--ds-border);
  background: linear-gradient(180deg, #fff, #f7faff);
  padding: 28px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
}

.ui-state.compact {
  padding: 18px 14px;
}

.ui-state-icon-wrap {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ui-state-icon-wrap.loading {
  color: var(--ds-info);
  background: rgba(20, 115, 230, 0.1);
}

.ui-state-icon-wrap.empty {
  color: var(--ds-text-secondary);
  background: rgba(117, 130, 159, 0.12);
}

.ui-state-icon-wrap.error {
  color: var(--ds-error);
  background: rgba(229, 57, 53, 0.1);
}

.ui-state-icon-wrap.offline {
  color: var(--ds-warning);
  background: rgba(242, 153, 0, 0.14);
}

.ui-state-title {
  margin: 4px 0 0;
  font-size: 16px;
  line-height: 1.35;
  color: var(--ds-text-primary);
}

.ui-state-description {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--ds-text-tertiary);
}

.ui-state-action {
  margin-top: 2px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.spinning {
  animation: ui-state-spin 1s linear infinite;
}

@keyframes ui-state-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

<script setup lang="ts">
import { computed } from 'vue'
import { NIcon } from 'naive-ui'

interface ActionItem {
  key: string
  title: string
  icon: any
  disabled?: boolean
}

const props = withDefaults(
  defineProps<{
    actions: ActionItem[]
    align?: 'left' | 'right'
  }>(),
  {
    align: 'left',
  },
)

const emit = defineEmits<{
  trigger: [key: string]
}>()

const alignClass = computed(() => (props.align === 'right' ? 'align-right' : 'align-left'))
</script>

<template>
  <div class="message-action-bar" :class="alignClass">
    <button
      v-for="action in actions"
      :key="action.key"
      class="action-btn"
      type="button"
      :title="action.title"
      :disabled="action.disabled"
      @click="emit('trigger', action.key)"
    >
      <n-icon :component="action.icon" />
    </button>
  </div>
</template>

<style scoped>
.message-action-bar {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.align-left {
  justify-content: flex-start;
  padding-left: 12px;
}

.align-right {
  justify-content: flex-end;
  padding-right: 12px;
}

.action-btn {
  border: none;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: transparent;
  color: var(--ds-text-tertiary);
  cursor: pointer;
  transition: background-color var(--ds-duration-fast) ease, color var(--ds-duration-fast) ease;
}

.action-btn:hover:not(:disabled) {
  background: var(--ds-bg-elevated);
  color: var(--ds-brand);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

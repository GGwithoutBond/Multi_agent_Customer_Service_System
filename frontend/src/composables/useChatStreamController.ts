import { computed, ref } from 'vue'

export type ChatStreamState = 'idle' | 'streaming' | 'stopped' | 'error' | 'offline'

export interface StreamRequestPayload<TAttachment = unknown> {
  content: string
  attachments?: TAttachment[]
  conversationId?: string
  webSearch: boolean
  personaStyle: string
}

export const useChatStreamController = <TAttachment = unknown>() => {
  const state = ref<ChatStreamState>('idle')
  const reason = ref('')
  const lastRequest = ref<StreamRequestPayload<TAttachment> | null>(null)
  const controller = ref<AbortController | null>(null)

  const canStop = computed(() => state.value === 'streaming' && !!controller.value)
  const canRecover = computed(
    () => !!lastRequest.value && ['stopped', 'error', 'offline'].includes(state.value),
  )

  const begin = (payload: StreamRequestPayload<TAttachment>) => {
    lastRequest.value = {
      ...payload,
      attachments: payload.attachments ? [...payload.attachments] : undefined,
    }
    controller.value = new AbortController()
    state.value = 'streaming'
    reason.value = ''
    return controller.value.signal
  }

  const finish = () => {
    controller.value = null
    state.value = 'idle'
    reason.value = ''
  }

  const stop = () => {
    if (!controller.value) return false
    controller.value.abort()
    controller.value = null
    state.value = 'stopped'
    reason.value = '已停止生成'
    return true
  }

  const fail = (message = '请求失败，请重试') => {
    controller.value = null
    state.value = 'error'
    reason.value = message
  }

  const offline = (message = '网络连接已中断，可重试恢复会话') => {
    controller.value = null
    state.value = 'offline'
    reason.value = message
  }

  const clearNotice = () => {
    if (state.value === 'streaming') return
    state.value = 'idle'
    reason.value = ''
  }

  return {
    state,
    reason,
    lastRequest,
    canStop,
    canRecover,
    begin,
    finish,
    stop,
    fail,
    offline,
    clearNotice,
  }
}

import request from '@/utils/request'

export function getMessages(conversationId: string) {
  return request({
    url: `/conversations/${conversationId}/messages`,
    method: 'get'
  })
}

export function getMessagesHistory(conversationId: string, beforeId?: string, limit = 30) {
  const params: Record<string, any> = { limit }
  if (beforeId) params.before_id = beforeId
  return request({
    url: `/conversations/${conversationId}/messages/history`,
    method: 'get',
    params
  })
}

export function uploadFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/upload',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export function getAvailableOrders() {
  return request({
    url: '/chat/orders/options',
    method: 'get'
  })
}

export function getAvailableProducts() {
  return request({
    url: '/chat/products/options',
    method: 'get'
  })
}

export function submitMessageFeedback(data: { message_id: string; rating: number; comment?: string }) {
  return request({
    url: '/chat/feedback',
    method: 'post',
    data
  })
}

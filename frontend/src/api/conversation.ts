import request from '@/utils/request'

export function createConversation(data: any) {
  return request({
    url: '/conversations',
    method: 'post',
    data
  })
}

export function updateConversation(id: string, data: any) {
  return request({
    url: `/conversations/${id}`,
    method: 'put',
    data
  })
}

export function getConversations() {
  return request({
    url: '/conversations',
    method: 'get'
  })
}

export function updateConversationPin(id: string, isPinned: boolean) {
  return request({
    url: `/conversations/${id}/pin`,
    method: 'patch',
    data: { is_pinned: isPinned }
  })
}

export function deleteConversation(id: string) {
  return request({
    url: `/conversations/${id}`,
    method: 'delete'
  })
}

export function batchDeleteConversations(conversationIds: string[]) {
  return request({
    url: '/conversations/batch-delete',
    method: 'post',
    data: { conversation_ids: conversationIds }
  })
}

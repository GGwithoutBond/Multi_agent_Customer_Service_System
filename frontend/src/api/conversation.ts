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

export function deleteConversation(id: string) {
  return request({
    url: `/conversations/${id}`,
    method: 'delete'
  })
}

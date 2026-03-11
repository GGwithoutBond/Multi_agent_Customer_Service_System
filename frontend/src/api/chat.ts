import request from '@/utils/request'

export function getMessages(conversationId: string) {
  return request({
    url: `/conversations/${conversationId}/messages`,
    method: 'get'
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

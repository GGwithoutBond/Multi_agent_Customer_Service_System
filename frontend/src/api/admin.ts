import request from '@/utils/request'

export function getDashboardMetrics() {
  return request({
    url: '/admin/dashboard/metrics',
    method: 'get'
  })
}

export function getModelLogs() {
  return request({
    url: '/admin/models/logs',
    method: 'get'
  })
}

export function getMiddlewareStatus() {
  return request({
    url: '/admin/middleware/status',
    method: 'get'
  })
}

/**
 * 获取 RAG 知识库与图谱监控状态
 */
export function getRAGStatus() {
  return request({
    url: '/admin/rag/status',
    method: 'get'
  })
}

/**
 * 获取 RAG 检索质量日志与聚合指标
 */
export function getRAGRetrievalLogs() {
  return request({
    url: '/admin/rag/retrieval-logs',
    method: 'get'
  })
}

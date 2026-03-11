import axios from 'axios'
import { useUserStore } from '@/stores/user'
import router from '@/router'

// Extend Window interface for discrete message API
declare global {
  interface Window {
    $message: any
  }
}

const service = axios.create({
  baseURL: '/api/v1',
  timeout: 50000 // Long timeout for AI generation potentially
})

// Request interceptor
service.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
service.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      const userStore = useUserStore()
      userStore.logout()
      router.push('/login')
    }
    window.$message?.error(error.message || 'Request Error')
    return Promise.reject(error)
  }
)

export default service

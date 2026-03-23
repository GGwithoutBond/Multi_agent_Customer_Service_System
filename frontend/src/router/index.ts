import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const LoginPage = () => import('@/views/LoginPage.vue')
const Chat = () => import('@/views/Chat.vue')
const Search = () => import('@/views/Search.vue')
const AdminLayout = () => import('@/layouts/AdminLayout.vue')
const Dashboard = () => import('@/views/admin/Dashboard.vue')
const ModelMonitor = () => import('@/views/admin/ModelMonitor.vue')
const MiddlewareMonitor = () => import('@/views/admin/MiddlewareMonitor.vue')
const RAGMonitor = () => import('@/views/admin/RAGMonitor.vue')

const router = createRouter({
    history: createWebHistory((import.meta as any).env.BASE_URL),
    routes: [
        {
            path: '/login',
            name: 'login',
            component: LoginPage,
            meta: { requiresAuth: false }
        },
        {
            path: '/',
            name: 'home',
            component: Chat,
            meta: { requiresAuth: true }
        },
        {
            path: '/chat/:id',
            name: 'chat',
            component: Chat,
            meta: { requiresAuth: true }
        },
        {
            path: '/search',
            name: 'search',
            component: Search,
            meta: { requiresAuth: true }
        },
        {
            path: '/admin',
            component: AdminLayout,
            meta: { requiresAuth: true },
            children: [
                {
                    path: '',
                    redirect: '/admin/dashboard'
                },
                {
                    path: 'dashboard',
                    name: 'admin-dashboard',
                    component: Dashboard
                },
                {
                    path: 'models',
                    name: 'admin-models',
                    component: ModelMonitor
                },
                {
                    path: 'middleware',
                    name: 'admin-middleware',
                    component: MiddlewareMonitor
                },
                {
                    path: 'rag',
                    name: 'admin-rag',
                    component: RAGMonitor
                }
            ]
        }
    ]
})

router.beforeEach((to, _from, next) => {
    const userStore = useUserStore()
    if (to.meta.requiresAuth && !userStore.isAuthenticated) {
        next('/login')
    } else if (to.path === '/login' && userStore.isAuthenticated) {
        next('/')
    } else {
        next()
    }
})

export default router

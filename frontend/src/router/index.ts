import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
// @ts-ignore
import LoginPage from '@/views/LoginPage.vue'
// @ts-ignore
import Chat from '@/views/Chat.vue'
// @ts-ignore
import Search from '@/views/Search.vue'
// @ts-ignore
import AdminLayout from '@/layouts/AdminLayout.vue'
// @ts-ignore
import Dashboard from '@/views/admin/Dashboard.vue'
// @ts-ignore
import ModelMonitor from '@/views/admin/ModelMonitor.vue'
// @ts-ignore
import MiddlewareMonitor from '@/views/admin/MiddlewareMonitor.vue'
// @ts-ignore
import RAGMonitor from '@/views/admin/RAGMonitor.vue'

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

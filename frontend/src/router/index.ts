import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
// @ts-ignore
import LoginPage from '@/views/LoginPage.vue'
// @ts-ignore
import Chat from '@/views/Chat.vue'
// @ts-ignore
import Search from '@/views/Search.vue'

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

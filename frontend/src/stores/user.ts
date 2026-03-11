import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
    state: () => ({
        token: localStorage.getItem('token') || '',
        user: null as any | null
    }),
    getters: {
        isAuthenticated: (state) => !!state.token
    },
    actions: {
        setToken(token: string) {
            this.token = token
            localStorage.setItem('token', token)
        },
        logout() {
            this.token = ''
            this.user = null
            localStorage.removeItem('token')
        }
    }
})

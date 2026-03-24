import { createApp } from 'vue'
import { createPinia } from 'pinia'
// @ts-ignore
import App from './App.vue'
import router from './router'
import { applyThemeCssVariables } from './theme/tokens'
import './index.css'
import './styles/design-system.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)

applyThemeCssVariables()
app.mount('#root')

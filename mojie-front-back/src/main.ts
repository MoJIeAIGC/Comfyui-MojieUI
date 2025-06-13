
import { createApp } from 'vue'
import { createPinia } from 'pinia'

//全量引入element-plus

import ElementPlus from 'element-plus'

import "@/styles/basic.scss"
import 'element-plus/theme-chalk/dark/css-vars.css'
import 'element-plus/dist/index.css';
import "@/styles/var.scss"
import "@/styles/element.scss"
import "@/styles/transition.scss"

import App from './App.vue'
import router from './router'
import { createHead } from '@unhead/vue'
import {i18n} from "@/messages/i18n";
import piniaPersist from 'pinia-plugin-persist'

const app = createApp(App)
const head = createHead()

app.use(i18n)
app.use(head)

app.use(ElementPlus)
const pinia = createPinia()
pinia.use(({store})=>{
    store.$router = router
})
pinia.use(piniaPersist)

app.use(pinia)
app.use(router)
app.mount('#app')

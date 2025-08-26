import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createI18n } from 'vue-i18n';

import App from './App.vue'
import router from './router'
import { useMainStore } from '@/stores/main.js'

import './css/main.css'
import zhCN from './locales/zh-CN.json';
import en from './locales/en.json';

// Init Pinia
const pinia = createPinia()

// Initialize i18n
const i18n = createI18n({
  locale: 'zh-CN', // 默认语言为中文
  messages: {
    'zh-CN': zhCN,
    en: en,
  },
});

// Create Vue app
createApp(App).use(router).use(pinia).use(i18n).mount('#app')

// Init main store
const mainStore = useMainStore(pinia)

// Fetch sample data
mainStore.fetchSampleClients()
mainStore.fetchSampleHistory()


// Dark mode: 自动根据本地存储或系统偏好切换主题
import { useDarkModeStore } from './stores/darkMode'
const darkModeStore = useDarkModeStore(pinia)
if (
  (!localStorage['darkMode'] && window.matchMedia('(prefers-color-scheme: dark)').matches) ||
  localStorage['darkMode'] === '1'
) {
  darkModeStore.set(true)
}

// Default title tag
const defaultDocumentTitle = 'Admin One Vue 3 Tailwind'

// Set document title from route meta
router.afterEach((to) => {
  document.title = to.meta?.title
    ? `${to.meta.title} — ${defaultDocumentTitle}`
    : defaultDocumentTitle
})

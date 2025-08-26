
<script setup>
import { RouterView } from 'vue-router'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import { useDarkModeStore } from '@/stores/darkMode.js'
import { computed } from 'vue'

const darkModeStore = useDarkModeStore()
const appClass = computed(() => darkModeStore.isEnabled ? 'dark' : '')
</script>

<template>
  <div id="app" :class="appClass">
    <LanguageSwitcher />
    <RouterView />
  </div>
</template>

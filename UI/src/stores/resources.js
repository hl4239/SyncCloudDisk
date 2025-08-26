import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchResources } from '@/api/api'

export const useResourcesStore = defineStore('resources', () => {
  const resources = ref([])
  const success = ref(false)
  const message = ref('')

  async function getResources(tv_cate = '热门-国产剧', count = 10) {
    try {
      const res = await fetchResources({ tv_cate, count })
      success.value = res.data.success
      message.value = res.data.message
      resources.value = res.data.data // 适配响应模型中的 data 字段
    } catch (error) {
      alert(error.message)
    }
  }

  return {
    resources,
    success,
    message,
    getResources,
  }
})

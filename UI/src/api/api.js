import axios from 'axios'

export const API_BASE_URL = 'http://192.168.31.2:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

export function fetchResources(params = {}) {
  // params 可包含 tv_cate, count 等查询参数
  return apiClient.get('/resources', { params })
}

export function createSyncTopMetaTask({ tv_cate, count }) {
  return apiClient.post('/tasks', {
    task_type: 'sync_top_metadata',
    priority: 'normal',
    parameters: {
      tv_cate,
      count: String(count),
    },
  })
}

export function fetchTaskStatus(taskId) {
  return apiClient.get(`/tasks/${taskId}`)
}

// 可继续扩展其他接口方法，如：
// export function fetchTasks() {
//   return apiClient.get('/tasks')
// }

export default apiClient

<script setup>

import { ref, computed, onMounted } from 'vue'
import { useResourcesStore } from '@/stores/resources'
import TableCheckboxCell from './TableCheckboxCell.vue'
import FormControl from './FormControl.vue'
import { createSyncTopMetaTask, fetchTaskStatus } from '@/api/api'

const resourcesStore = useResourcesStore()
const tvCateOptions = [
  { label: '热门-国产剧', value: '热门-国产剧' },
  { label: '热门-欧美剧', value: '热门-欧美剧' },
  { label: '热门-日剧', value: '热门-日剧' },
  { label: '热门-韩剧', value: '热门-韩剧' },
  { label: '热门-动画', value: '热门-动画' },
  { label: '其他', value: '其他' },
]
const selectedTvCate = ref(tvCateOptions[0].value)
const countOptions = [10, 20, 50, 100]
const selectedCount = ref(countOptions[0])
const syncTvCate = ref(tvCateOptions[0].value)
const syncCount = ref(countOptions[0])
const isSyncing = ref(false)

const perPage = selectedCount
const currentPage = ref(0)
const checkedRows = ref([])
const checkable = true
const showTaskModal = ref(false)
const taskStatus = ref(null)
const pollingTimer = ref(null)

function fetchResources() {
  resourcesStore.getResources(selectedTvCate.value, selectedCount.value)
  checkedRows.value = []
  currentPage.value = 0
}

onMounted(() => {
  fetchResources()
})

const itemsPaginated = computed(() =>
  resourcesStore.resources.slice(perPage.value * currentPage.value, perPage.value * (currentPage.value + 1))
)
const numPages = computed(() => Math.ceil(resourcesStore.resources.length / perPage.value))
const pagesList = computed(() => Array.from({ length: numPages.value }, (_, i) => i))
const currentPageHuman = computed(() => currentPage.value + 1)

function checked(val, item) {
  if (val) {
    if (!checkedRows.value.includes(item.id)) checkedRows.value.push(item.id)
  } else {
    checkedRows.value = checkedRows.value.filter(id => id !== item.id)
  }
}

function checkedAllCurrentPage() {
  const ids = itemsPaginated.value.map(item => item.id)
  const allChecked = ids.every(id => checkedRows.value.includes(id))
  if (allChecked) {
    checkedRows.value = checkedRows.value.filter(id => !ids.includes(id))
  } else {
    checkedRows.value = Array.from(new Set([...checkedRows.value, ...ids]))
  }
}

async function submitSyncTopMeta() {
  isSyncing.value = true
  try {
    const res = await createSyncTopMetaTask({
      tv_cate: syncTvCate.value,
      count: syncCount.value ?? syncCount,
    })
    const taskId = res.data.data?.id
    if (!taskId) throw new Error('任务ID获取失败')
    taskStatus.value = null
    pollTaskStatus(taskId)
  } catch (e) {
    alert('任务创建失败：' + (e?.message || e))
    showTaskModal.value = false
  } finally {
    isSyncing.value = false
  }
}

async function pollTaskStatus(taskId) {
  try {
    const res = await fetchTaskStatus(taskId)
    taskStatus.value = res.data.data
    if (taskStatus.value.status !== 'completed') {
      pollingTimer.value = setTimeout(() => pollTaskStatus(taskId), 1500)
    } else {
      clearTimeout(pollingTimer.value)
    }
  } catch (e) {
    clearTimeout(pollingTimer.value)
    alert('任务状态查询失败：' + (e?.message || e))
    showTaskModal.value = false
  }
}

function closeTaskModal() {
  showTaskModal.value = false
  clearTimeout(pollingTimer.value)
}
</script>


<template>
  <div>
    <div class="flex items-center mb-4 gap-4">
      <button
        class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 transition"
        @click="showTaskModal = true"
      >
        同步豆瓣Top榜
      </button>
      <FormControl
        :options="tvCateOptions"
        v-model="selectedTvCate"
        type="select"
        @change="fetchResources"
        class="w-48"
        name="tv_cate"
      />
      <FormControl
        :options="countOptions.map(c=>({label:c,value:c}))"
        v-model="selectedCount"
        type="select"
        @change="fetchResources"
        class="w-32"
        name="count"
      />
    </div>
    <div v-if="showTaskModal" class="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
      <div class="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-6 w-96">
        <h3 class="text-lg font-bold mb-2">豆瓣Top榜同步任务</h3>
        <form @submit.prevent="submitSyncTopMeta">
          <FormControl
            :options="tvCateOptions"
            v-model="syncTvCate"
            type="select"
            class="w-full mb-2"
            name="sync_tv_cate"
          />
          <FormControl
            :options="countOptions.map(c=>({label:c,value:c}))"
            v-model="syncCount"
            type="select"
            class="w-full mb-4"
            name="sync_count"
          />
          <button type="submit" class="w-full px-4 py-2 bg-blue-600 text-white rounded" :disabled="isSyncing">
            {{ isSyncing ? '任务创建中...' : '开始同步' }}
          </button>
        </form>
        <div v-if="taskStatus">
          <p>任务状态：{{ taskStatus.status }}</p>
          <p>进度：{{ taskStatus.progress }}%</p>
          <p v-if="taskStatus.status === 'completed'">结果：{{ taskStatus.result?.status }}，已同步分类：{{ taskStatus.result?.synced_category }}</p>
        </div>
        <button class="mt-6 px-4 py-2 bg-gray-500 text-white rounded" @click="closeTaskModal">关闭</button>
      </div>
    </div>
    <table class="table-auto w-full">
      <thead>
        <tr>
          <th v-if="checkable">
            <label class="checkbox">
              <input type="checkbox"
                :checked="itemsPaginated.length > 0 && itemsPaginated.every(item => checkedRows.includes(item.id))"
                @change="checkedAllCurrentPage"
              />
              <span class="check" />
            </label>
          </th>
          <th>名称</th>
          <th>剧集</th>
          <th>同步状态</th>
          <th>更新时间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in itemsPaginated" :key="item.id">
          <TableCheckboxCell v-if="checkable" :checked="checkedRows.includes(item.id)" @checked="checked($event, item)" />
          <td>{{ item.title }}</td>
          <td>{{ item.episodes_info?.total_episodes || '无数据' }}</td>
          <td>
            <span v-if="item.cloud_disk_info?.accounts?.length">
              {{ item.cloud_disk_info.accounts[0].is_sync_finish ? '已同步' : '未同步' }}
            </span>
            <span v-else>无数据</span>
          </td>
          <td>{{ item.last_metadata_update_time }}</td>
        </tr>
      </tbody>
    </table>
    <div class="p-3 lg:px-6 border-t border-gray-100 dark:border-slate-800">
      <div class="flex justify-between items-center">
        <div>
          <span class="text-sm text-gray-600">已选择ID：{{ checkedRows.join(', ') }}</span>
        </div>
        <div class="flex items-center">
          <button
            v-for="page in pagesList"
            :key="page"
            @click="currentPage = page"
            :class="['px-2 py-1 mx-1', currentPage === page ? 'bg-blue-500 text-white' : 'bg-gray-200']"
          >
            {{ page + 1 }}
          </button>
          <small class="ml-2">第 {{ currentPageHuman }} 页 / 共 {{ numPages }} 页</small>
        </div>
      </div>
    </div>
  </div>
</template>

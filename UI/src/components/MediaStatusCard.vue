<template>
  <CardBox :isHoverable="true" :rounded="'rounded-xl'">
    <div class="p-4">
      <h2 class="text-lg font-bold mb-2">{{ mediaName }}</h2>
      <div class="mb-1">
        <span class="font-semibold">全网最新剧集：</span>
        <span>{{ latestEpisode }}</span>
      </div>
      <div>
        <span class="font-semibold">网盘同步状态：</span>
        <span :class="statusClass">{{ syncStatus }}</span>
      </div>
    </div>
  </CardBox>
</template>

<script setup>
import { computed } from 'vue'
import CardBox from './CardBox.vue'

const props = defineProps({
  mediaName: {
    type: String,
    required: true,
  },
  latestEpisode: {
    type: String,
    required: true,
  },
  syncStatus: {
    type: String,
    required: true,
  },
})

const statusClass = computed(() => {
  switch (props.syncStatus) {
    case '已同步':
      return 'text-green-600';
    case '未同步':
      return 'text-red-600';
    case '部分同步':
      return 'text-yellow-600';
    default:
      return '';
  }
})
</script>

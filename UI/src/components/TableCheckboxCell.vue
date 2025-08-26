
<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  type: {
    type: String,
    default: 'td',
  },
  checked: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['checked'])

function onChange(e) {
  emit('checked', e.target.checked)
}
</script>


<template>
  <component :is="type" class="lg:w-1">
    <label class="checkbox">
      <input :checked="checked" type="checkbox" @change="onChange" />
      <span class="check" />
    </label>
  </component>
</template>

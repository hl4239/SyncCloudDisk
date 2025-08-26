<template>
  <div>
    <button @click="switchToChinese">切换到中文</button>
    <button @click="switchToEnglish">Switch to English</button>
    <h1>{{ $t('welcome') }}</h1>
  </div>
</template>

<script>
export default {
  methods: {
    switchToChinese() {
      this.$i18n.locale = 'zh-CN';
    },
    switchToEnglish() {
      this.$i18n.locale = 'en';
    },
  },
};
</script>

<script setup lang="ts">
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
const { Sunny,Moon } = ElementPlusIconsVue
import { useDark } from '@vueuse/core'
import SunnyIcon from "@/components/headers/SunnyIcon.vue";
const isDark = useDark()

</script>
<template>
  <el-switch
      v-model="isDark"
      class="mt-2"
      inline-prompt
      :active-icon="SunnyIcon"
      :inactive-icon="Moon"
  />
</template>

<style scoped>

</style>
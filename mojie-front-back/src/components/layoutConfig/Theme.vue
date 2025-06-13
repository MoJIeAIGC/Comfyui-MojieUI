<script setup lang="ts">
import ThemeBlock from "@/components/layoutConfig/ThemeBlock.vue";
import {ref} from "vue";

import colors from "@/theme/colors";
import {useThemeStore} from "@/store/theme-store";

const current = ref(colors[0])

const theme=useThemeStore()

function change(color: string) {
  current.value = color
  theme.setPrimary(color)
}

onMounted(() => {
  current.value = useThemeStore().primary
})
</script>
<template>
  <div class="theme">
    <ThemeBlock v-for="color in colors" :color="color" :active="current==color" @change="change"/>
    <el-color-picker v-model="current" size="large" @change="change"/>
  </div>
</template>
<style lang="scss" scoped>
.theme {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
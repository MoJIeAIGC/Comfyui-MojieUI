<script setup lang="ts">

import {Setting} from "@element-plus/icons-vue";
import {ref} from "vue"
import LayoutConfig from "@/components/layoutConfig/LayoutConfig.vue";
//打开右侧设置
const drawer = ref(false)

</script>

<template>
  <el-button :icon="Setting" circle text @click="drawer=true"></el-button>
  <el-drawer v-model="drawer" :with-header="false" size="350px">
    <LayoutConfig @close="drawer=false"/>
  </el-drawer>
</template>

<style scoped>

</style>
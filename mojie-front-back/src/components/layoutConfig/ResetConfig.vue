<script setup lang="ts">
import {ElMessage} from "element-plus";
import {useStorage} from "@vueuse/core";
import {useThemeStore} from "@/store/theme-store";
import {useTabsStore} from "@/store/tabs-store";

const collapse=useStorage('collapse',false)
const themeStore=useThemeStore()
const tabsStore=useTabsStore()

function reset() {
  collapse.value=false
  themeStore.reset()
  tabsStore.reset()
  ElMessage.success("Reset config success.");
}
</script>

<template>
  <div class="reset">
    <div class="btn-box">
      <el-button type="primary" @click="reset">{{$t('Reset')}}</el-button>
    </div>
  </div>
</template>

<style scoped>
.reset{
  padding-top: 30px;
}
.btn-box {
  display: flex;
  .el-button{
    flex: 1;
  }
}
</style>
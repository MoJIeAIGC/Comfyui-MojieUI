<script setup lang="ts">
//折叠展开
import {useDark, useStorage} from "@vueuse/core";
import UserInfo from "@/components/headers/UserInfo.vue";
import SwitchDarkMode from "@/components/headers/SwitchDarkMode.vue";
import SwitchLanguage from "@/components/headers/SwitchLanguage.vue";
import {ArrowRight, Expand, Fold, Refresh} from "@element-plus/icons-vue";
import SettingButton from "@/components/headers/SettingButton.vue";
import {useThemeStore} from "@/store/theme-store";
import {computed} from "vue";
import Breadcrumb from "@/components/headers/Breadcrumb.vue";
import SearchButton from "@/components/headers/SearchButton.vue";

const collapse = useStorage("collapse", false)
const toggleCollapse = () => {
  collapse.value = !collapse.value
}
const themeStore = useThemeStore()
//是否启用面包屑
const hasBreadcrumb = computed(() => {
  return themeStore.breadcrumb
})

const isDark = useDark()
//找到当前的路由对应的sidebar菜单
const topDark=computed(()=>{
  return !isDark.value&&themeStore.themeLayout==="dark"
})
</script>

<template>
  <header :class="{header:true,dark:topDark}">
    <div class="left">
    <el-button text @click="toggleCollapse">
      <el-icon :size="20">
        <Expand v-if="collapse"/>
        <Fold v-else/>
      </el-icon>
    </el-button>
      <!-- 面包屑 -->
      <Breadcrumb v-if="hasBreadcrumb"/>
    </div>
    <div class="space"></div>
    <div class="right">
      <SearchButton/>
      <SwitchDarkMode/>
      <SwitchLanguage/>
      <UserInfo/>
      <SettingButton/>
    </div>
  </header>
</template>

<style scoped lang="scss">
$dark-color: #CFD3DC;
.dark{
  background-color: #131313;

  --el-text-color-regular: #FFF;
  --el-text-color-secondary: $dark-color;



  --el-fill-color-light: #666;
  --el-fill-color: #666;
  --el-border-color: #666;

  --el-drawer-bg-color: #131313;
}
.header {
  //box-shadow: 0 1px 4px rgba(0, 21, 41, .08);
  padding: 0 10px;
  display: flex;
  align-items: center;
  flex-direction: row;
  //background-color: #000;
  .space {
    flex: 1;
  }

  .right {
    display: flex;
    align-items: center;
    gap: 15px;
    padding-right: 10px;
  }

}
</style>
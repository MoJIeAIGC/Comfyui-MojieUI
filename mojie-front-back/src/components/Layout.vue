<script setup lang="ts">

import Sidebar from "@/components/Sidebar.vue";
import LayoutHeader from "@/components/LayoutHeader.vue";
import {computed, onMounted} from "vue";
import TabsView from "@/components/tabs/TabsView.vue";
import {useThemeStore} from "@/store/theme-store";
const show=ref(false);

onMounted(()=>{
  //延迟50ms 防止页面闪一下
  setTimeout(()=>{
    show.value=true;
  },50)
})

const themeStore=useThemeStore();
const showTabs=computed(()=>{
  return themeStore.tabs;
})
</script>
<template>
  <div class="layout" v-cloak v-show="show">
    <el-container>
      <el-aside class="aside">
        <Sidebar class="sidebar"/>
      </el-aside>
      <el-container>
        <el-header class="header">
          <LayoutHeader/>
        </el-header>
        <TabsView v-if="showTabs"/>
        <el-main class="main">
          <slot></slot>
        </el-main>
      </el-container>
    </el-container>
  </div>

</template>
<style lang="scss">
.layout {
  height: 100%;
  display: flex;

  .aside {
    display: flex;
    width: auto;
    box-shadow: 2px 0 8px #1d23290d;
    z-index: 101;
  }

  flex-direction: row;

  .header {
    padding: 0;
    height: 54px;
    //底部阴影
    box-shadow: 0 2px 8px #1d23290d;
    z-index: 102;
  }

  .main {
    display: flex;
    flex-direction: column;
    overflow: auto;
    background-color: var(--component-bg);
    padding: 0;
  }
}
</style>
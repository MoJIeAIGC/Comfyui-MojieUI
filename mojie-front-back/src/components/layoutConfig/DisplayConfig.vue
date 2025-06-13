<script setup lang="ts">

import {useThemeStore} from "@/store/theme-store";
import {Check} from "@element-plus/icons-vue";
import {useDark} from "@vueuse/core";
import {watch} from "vue";

const styles = [{
  left: "#323547",
  top: "#FFFFFF",
  name: "default"
}, {
  left: "#FFFFFF",
  top: "#FFFFFF",
  name: "light"
}, {
  left: "#323547",
  top: "#323547",
  name: "dark"
}]
const body = "#f0f2f5"
const themeStore = useThemeStore()

function change(item: any) {
  themeStore.setThemeLayout(item.name)
}
const isDark = useDark()
watch(isDark, (val) => {
  if(val){
    themeStore.setThemeLayout("default")
  }
})

const breadcrumb = computed({
  get() {
    return themeStore.breadcrumb
  },
  set(val) {
    themeStore.setBreadcrumb(val)
  }
})
const tabs = computed({
  get() {
    return themeStore.tabs
  },
  set(val) {
    themeStore.setTabs(val)
  }
})

</script>

<template>
  <div>
    <el-divider>
      {{ $t("Navigation bar") }}
    </el-divider>
    <div class="grid">
      <template v-for="item in styles">
        <div class="item flex" @click="change(item)" v-if="!isDark||item.name==='dark'">
          <el-icon color="var(--primary-color)" class="icon" :size="20" v-if="themeStore.themeLayout === item.name">
            <Check/>
          </el-icon>
          <div class="left" :style="{ backgroundColor: item.left }"></div>
          <div class="right">
            <div class="top" :style="{ backgroundColor: item.top }"></div>
            <div class="body" :style="{backgroundColor:body}"></div>
          </div>
        </div>
      </template>
    </div>
    <el-divider>{{$t("Display")}}</el-divider>
    <el-row>
      <el-col :span="20">
        {{ $t("Breadcrumb") }}
      </el-col>
      <el-col :span="4">
        <el-switch v-model="breadcrumb" />
      </el-col>
    </el-row>
    <el-row>
      <el-col :span="20">
        {{ $t("Tabs") }}
      </el-col>
      <el-col :span="4">
        <el-switch v-model="tabs" />
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.grid {
  display: flex;
  gap: 20px;
  //居中
  justify-content: center;
  align-items: center;

  .item {
    cursor: pointer;
    position: relative;
    width: 40px;
    height: 40px;
    display: flex;
    flex-direction: row;
    box-shadow: 0px 1px 2px rgba(0, 0, 0, 0.3);
    border-radius: 5px;
    overflow: hidden;

    .icon {
      position: absolute;
      top: 10px;
      right: 10px;
    }

    .left {
      width: 10px;
      height: 100%;
    }

    .right {
      flex: 1 1 0;
      height: 100%;
      display: flex;
      flex-direction: column;
      gap: 0;

      .top {
        height: 10px;
        width: 100%;
      }

      .body {
        flex: 1 1 0;
        width: 100%;
      }
    }
  }
}
</style>
<script setup lang="ts">

import {computed, nextTick, onUpdated, watch} from "vue";


//导入element-plus语言包
import zhCn from "element-plus/dist/locale/zh-cn.mjs"
import en from "element-plus/dist/locale/en.mjs"
import {setPrimaryColor} from "@/theme";

import {useThemeStore} from "@/store/theme-store";
import {useLocaleStore} from "@/store/locale";
import Layout from "@/components/Layout.vue";
import {useRoute} from "vue-router";
import {useTransitionStore} from "@/store/transition-store";

const maps = {
  "zh": zhCn,
  "en": en,
}

const localeStore = useLocaleStore()
const locale = computed(() => {
  return maps[localeStore.locale] || zhCn
})
const theme = useThemeStore()
onMounted(() => {
  //读取默认主题色
  setPrimaryColor(useThemeStore().primary)
  theme.setThemeLayout(theme.themeLayout)
})
const route = useRoute()
const transitionStore = useTransitionStore()
const transitionName = computed(() => {
  return transitionStore.enable ? transitionStore.type : ""
})
</script>
<template>
  <el-config-provider :locale="locale">
    <router-view v-slot="{Component,route}">
      <component v-if="route.name==='login'" :is="Component" :key="route.path"/>
      <layout v-else>
        <transition :name="transitionName" mode="out-in">
          <!-- <keep-alive> -->
            <component :is="Component" :key="route.path"/>
          <!-- </keep-alive> -->
        </transition>
      </layout>
    </router-view>
  </el-config-provider>
</template>


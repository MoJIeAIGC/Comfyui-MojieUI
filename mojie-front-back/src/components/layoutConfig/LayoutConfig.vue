<script setup lang="ts">

import {Close} from "@element-plus/icons-vue";
import Theme from "@/components/layoutConfig/Theme.vue";
import SwitchDarkMode from "@/components/headers/SwitchDarkMode.vue";
import {useDark} from "@vueuse/core";
import PageTransition from "@/components/layoutConfig/PageTransition.vue";
import DisplayConfig from "@/components/layoutConfig/DisplayConfig.vue";
import ResetConfig from "@/components/layoutConfig/ResetConfig.vue";

const emit = defineEmits(["close"]);
const isDark = useDark()

</script>

<template>
  <div>
    <div class="flex flex-space-between ">
      <span style="font-size: 1.25rem;">{{ $t("Layout config") }}</span>
      <el-button @click="emit('close')" :icon="Close" circle text></el-button>
    </div>
    <el-divider>
      {{ $t("Theme mode") }}
    </el-divider>
    <div class="flex justify-center gap-10">
      <div :class="{'text-active':!isDark}">{{$t("light")}}</div>
      <SwitchDarkMode/>
      <div  :class="{'text-active':isDark}">{{$t("dark")}}</div>
    </div>

    <el-divider>
      {{ $t("Theme color") }}
    </el-divider>
    <Theme/>

    <DisplayConfig/>
    <PageTransition/>
    <ResetConfig/>
  </div>
</template>

<style>
.text-active{
  color: var(--el-color-primary);
}
:root{
  font-size: 14px;
}
</style>
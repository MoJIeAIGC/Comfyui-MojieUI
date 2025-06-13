<script setup lang="ts">

import IconLanguage from "@/components/icons/IconLanguage.vue";
import {onMounted} from "vue";
import {useI18n} from "vue-i18n";
import {useStorage} from "@vueuse/core";
import {Check} from "@element-plus/icons-vue";


//获取当前语言
import {i18n, t} from "@/messages/i18n";
import {useLocaleStore} from "@/store/locale";

const languages = ref([])
onMounted(() => {
  //定义一个数组
  let locales = []
  i18n.global.availableLocales.forEach((item) => {
    locales.push({
      name: t(item),
      code: item
    })
    languages.value = locales
  })
})

const localeStore=useLocaleStore()

function change(item: any) {
  i18n.global.locale = item.code
  localeStore.setLocale(item.code)
}
</script>

<template>

  <el-dropdown trigger="click">
    <el-button text :icon="IconLanguage" circle></el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item v-for="item in languages" @click="change(item)">
          <el-icon v-if="localeStore.locale==item.code">
            <Check/>
          </el-icon>
          <el-icon v-else></el-icon>
          <span v-text="item.name"></span>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style scoped>

</style>
<script setup lang="ts">
import SubMenu from "@/components/sidebar/SubMenu.vue";
import {Document, Link} from "@element-plus/icons-vue";
import {computed} from "vue";
import type {MenuType} from "@/types";
import {useStorage} from "@vueuse/core";
import {useTabsStore} from "@/store/tabs-store";

const props = defineProps({
  menu: {
    type: Object,
    default: () => ({})
  }
})

const hasItemChild = (item: any) => {
  return item.children && item.children.length > 0
}
const router = useRouter()

const emit = defineEmits(['open'])
const tabs = useTabsStore()
const open = () => {
  let menu = props.menu as MenuType
  tabs.pushTab({
    id: menu.id,
    text: menu.text,
    closeable: true,
    external: menu.external,
    url: menu.url,
    active: true
  })
}

const hasChild = computed(() => {
  return props.menu.children && props.menu.children.length > 0
})

//判断是否折叠
const collapse = useStorage("collapse", false)
</script>

<template>
  <SubMenu v-if="hasChild" :menu="menu" @open="open"/>
  <div v-else @click="open">
    <el-menu-item :index="`${menu.id}`">
      <el-icon>
        <document/>
      </el-icon>
      <span>{{ menu.text }}</span>
      <SubMenu :menu="menu" v-if="hasItemChild(menu)" @open="open"/>
    </el-menu-item>
  </div>
</template>

<style scoped>

</style>
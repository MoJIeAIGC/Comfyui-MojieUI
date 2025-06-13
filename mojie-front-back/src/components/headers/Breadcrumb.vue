<script setup lang="ts">

import {ArrowDown, ArrowRight} from "@element-plus/icons-vue";
import {computed, onMounted, ref, watch} from "vue";
import {useStorage} from "@vueuse/core";
import {useTabsStore} from "@/store/tabs-store";
import {useMenusStore} from "@/store/menu-store";

const paths = ref([])


const menusStore = useMenusStore()

const tabsStore = useTabsStore()
watch(() => tabsStore.defaultActive, (val) => {
  process(val)
}, {
  immediate: false,
})
const menus=computed(()=>{
  return menusStore.menus
})
watch(() => menusStore.menus, (val) => {
  process(tabsStore.defaultActive)
})
async function process(activeId:string) {
  let find = deepFind(menus.value, activeId);
  paths.value=[]
  find.forEach(item => {
    paths.value.push(item)
  })
}

function deepFind(items: any[], id: string) {
  let path = []
  //从items顶级开始寻找，记录下父级
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (item.id.toString() === id) {
      path.push(item)
      break
    } else if (item.children && item.children.length > 0) {
      const result = deepFind(item.children, id)
      if (result.length > 0) {
        path.push(item)
        path.push(...result)

      }
    }
 }
  return path
}
const open = (item: any) => {
  tabsStore.pushTab(item)
}
</script>

<template>
  <el-breadcrumb :separator-icon="ArrowRight">
    <el-breadcrumb-item v-for="item in paths">
      <el-dropdown trigger="click"  v-if="item.children">
          <span class="el-dropdown-link">
            {{item.text}}
          </span>
        <template #dropdown>
          <el-dropdown-menu>
            <template v-for="child in item.children">
              <el-dropdown-item v-if="!child.children" @click="open(child)">{{child.text}}</el-dropdown-item>
              <el-dropdown-item v-else disabled>{{child.text}}</el-dropdown-item>
            </template>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <span v-else>{{item.text}}</span>
    </el-breadcrumb-item>
  </el-breadcrumb>
</template>

<style scoped>
.el-dropdown-link{
  cursor: pointer;
}
</style>
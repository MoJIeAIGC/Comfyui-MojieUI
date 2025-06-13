<script setup lang="ts">
import {Document} from "@element-plus/icons-vue";
import SubItem from "@/components/sidebar/SubItem.vue";
import {computed} from "vue";

const props = defineProps({
  menu: {
    type: Object,
    default: () => ({})
  }
})
const hasChild = computed(()=>{
  return props.menu.children && props.menu.children.length > 0
})

const emit = defineEmits(['open'])
const open = (item:any) => {
  emit('open', item)
}

</script>

<template>
  <el-sub-menu v-if="hasChild" :index="`${menu.id}`">
    <template #title>
      <el-icon>
        <document/>
      </el-icon>
      <span>{{ menu.text }}</span>
    </template>
    <SubItem v-for="(item, index) in menu.children" :key="index" :menu="item" @open="open"/>
  </el-sub-menu>
  <SubItem v-else :menu="menu" @open="open"/>
</template>

<style scoped>

</style>
<script setup lang="ts">

import {InfoFilled} from "@element-plus/icons-vue";
import {computed, watch, ref} from "vue";
import {useCssVar} from "@vueuse/core";
import {useThemeStore} from "@/store/theme-store";
//计算属性 style
const color=ref(null)
const style = computed(() => {
  color.value = useCssVar('--primary-color')
  let r = color.value
  //hex转rgb
  //@ts-ignore
  const rgb = r.value.match(/^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i).slice(1).map(x => parseInt(x, 16))
  return {
    backgroundColor: `rgba(${rgb.join(',')}, 0.1)`,
    border: 'var(--primary-color) 1px solid',
  }
})

const props = defineProps({
  show: {
    type: Boolean,
    default: true
  }
})
const theme=useThemeStore()
watch(()=>theme.primary, (val) => {
  console.log("primary改变",val)
  //通知style改变
  color.value=val
})
const all = ref(false)
</script>

<template>
  <div class="data-alert" :style="style" v-if="show">
    <div class="left">
      <el-icon class="primary">
        <InfoFilled/>
      </el-icon>
      <span>已选择: 0 条数据</span>
    </div>
    <div class="right">
      <el-link v-if="!all" type="success" @click="all=true">选择全部(100)</el-link>
      <el-link v-if="all" type="primary" @click="all=false">取消选择全部(100)</el-link>
    </div>
  </div>
</template>

<style scoped lang="scss">
.data-alert {
  user-select: none;
  display: block;
  padding: 10px;
  border-radius: 5px;
  border: var(--primary-color) 1px solid;
  margin: 20px auto;

  .primary {
    color: var(--primary-color);
  }

  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  .left,.right{
    display: flex;
    align-items: center;
    gap: 10px;
  }
}
</style>
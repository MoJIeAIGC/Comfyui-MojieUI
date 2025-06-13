<script setup lang="ts">

import {ArrowDown, CircleClose, Close, DeleteFilled, Minus, Refresh} from "@element-plus/icons-vue";
import {ref, defineProps, computed} from "vue";

const props = defineProps({
  item: {
    type: Object,
    default: () => ({
      text: '',
      active: false,
      id: '',
      url: '',
      closeable: true,
    })
  }
})
const el = ref(null)

function getEl() {
  return el.value
}

defineExpose({
  getEl
})
const emit = defineEmits(['close', 'selected','closeOther','refresh','closeAll'])

const closeCurrent = () => {
  emit('close', props.item)
}
const closeOther = () => {
  emit('closeOther', props.item)
}
const closeAll = () => {
  emit('closeAll', props.item)
}
const refresh = () => {
  emit('refresh', props.item)
}


</script>

<template>

  <div :class="{tab:true,active:item.active}" ref="el" @click="emit('selected',item)">
    <span class="name">
        <el-dropdown trigger="contextmenu">
          <span class="el-dropdown-link">
            {{ item.text }}
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-if="item.active" @click="refresh" :icon="Refresh">{{ $t('Refresh') }}</el-dropdown-item>
              <el-dropdown-item :divided="item.active" @click="closeCurrent" :icon="CircleClose">{{ $t('Close current') }}</el-dropdown-item>
              <el-dropdown-item @click="closeOther" :icon="Minus">{{ $t('Close other') }}</el-dropdown-item>
              <el-dropdown-item @click="closeAll" :icon="Close">{{ $t('Close all') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

    </span>
    <span v-if="item.closeable" class="close" @click="emit('close',item)">
        <el-icon>
          <Close/>
        </el-icon>
    </span>
  </div>
</template>

<style scoped>
.name{
  display: flex;
  align-items: center;
  padding: 3px;
}
</style>
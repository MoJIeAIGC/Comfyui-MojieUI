<template>
  <div class="system-group">
    <div class="right-wp">
      <div class="tabs-flex flex">
        <div class="flex-1 text-center" :class="{active: item.type===_data.activeType}" v-for="item in _data.tabs"
             :key="item.type" @click="_data.activeType=item.type">{{ item.name }}
          <caret-down-outlined :style="tabIconStyle" v-if="item.type===_data.activeType"/>
        </div>
      </div>
      <div class="tool-box">
        <VideoGeneration ref="ColorAdjustmentRef" v-show="_data.activeType==='1'" @change="change"></VideoGeneration>
      </div>
    </div>
  </div>
</template>

<script setup>
import {reactive, defineExpose, defineProps, defineEmits,ref} from 'vue'
import {CaretDownOutlined} from '@ant-design/icons-vue';
import VideoGeneration from './rightTools/VideoGeneration.vue'
 const ColorAdjustmentRef = ref()
const emit = defineEmits(['change']);
const props = defineProps({

})
const _data = reactive({
  activeType: '1',
  src: '',
  tabs: [
     {type: '1', name: '视频生成'},
  ]
})
const change = (info) => {
  emit('change',info)
}
const tabIconStyle = {
  fontSize: '24px',
  color: '#405FFF'
}
const setType = (item, src) => {
  _data.src = src
  _data.activeType = item.type
}
defineExpose({
  setType
})

</script>

<style lang="less" scoped>
.system-group {
  margin: 10px 10px 10px 0;
  background: @bg-page-two-color;
  height: calc(100vh - 70px);
  border-radius: 8px;

  .right-wp {
    height: 100%;
    width: 400px;
    overflow: hidden;
    transition: .3s all;
    //display: flex;
    //flex-direction: column;
    .tabs-flex {
      height: 40px;
      font-size: 12px;

      > .flex-1 {
        position: relative;
        cursor: pointer;
        background: #444444;
        line-height: 40px;

        &.active {
          background: #405FFF;
        }

        &:first-child {
          border-radius: 8px 0 0;
        }

        &:last-child {
          border-radius: 0 8px 0 0;
        }

        :deep(.anticon) {
          position: absolute;
          top: 32px;
          left: calc(50% - 12px);
        }
      }
    }

    .tool-box {
      height: calc(100% - 40px);
      position: relative;
    }
  }
}

@media screen and (max-width: 1200px) {
  .system-group {
    .right-wp {
      //width: 300px;
    }
  }
}
</style>
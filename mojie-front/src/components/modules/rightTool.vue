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
        <ProductReplacement ref="ProductReplacementRef" v-show="_data.activeType==='1'" :chatId="chatId"  @no-points="noPoints"
                            @change="saveTask"></ProductReplacement>
        <refine ref="refineRef" v-show="_data.activeType==='2'" :chatId="chatId" @change="saveTask" @no-points="noPoints"></refine>
        <Extend ref="ExtendRef" v-show="_data.activeType==='3'" :chatId="chatId" @change="saveTask" @no-points="noPoints"></Extend>
        <Eliminate ref="EliminateRef" v-show="_data.activeType==='4'" :chatId="chatId" @change="saveTask" @no-points="noPoints"></Eliminate>
        <ColorAdjustment ref="ColorAdjustmentRef" v-show="_data.activeType==='5'" :chatId="chatId"  @no-points="noPoints"
                         @change="saveTask"></ColorAdjustment>
<!--        <div v-else>-->
<!--          <a-empty/>-->
<!--        </div>-->
      </div>
    </div>
  </div>
</template>

<script setup>
import {reactive, defineExpose, defineProps, defineEmits,ref} from 'vue'
import {CaretDownOutlined} from '@ant-design/icons-vue';
import ProductReplacement from './rightTools/ProductReplacement.vue'
import refine from './rightTools/Refine.vue'
import ColorAdjustment from './rightTools/ColorAdjustment.vue'
import Eliminate from './rightTools/Eliminate.vue'
import Extend from './rightTools/Extend.vue'
import emitter from '@/utils/emitter'
 const ProductReplacementRef = ref()
 const refineRef = ref()
 const ExtendRef = ref()
 const EliminateRef = ref()
 const ColorAdjustmentRef = ref()
const emit = defineEmits(['change','no-points']);
const props = defineProps({
  chatId: {
    type: [String, Number],
    default: ''
  },
  tab: {
    type:String,
    default:'chat'
  }
})
const _data = reactive({
  activeType: '1',
  src: '',
  tabs: [
    {type: '1', name: '迁移替换'},
    {type: '2', name: '局部重绘'},
    {type: '3', name: '智能扩图'},
    {type: '4', name: '内补消除'},
    // {type: '5', name: '添加文字'},
    {type: '5', name: '色彩调节'}
  ]
})
const saveTask = (info, id) => {
  if ((!props.chatId||props.chatId === -1||props.chatId === '-1')&&props.tab==='chat') {
    emitter.emit('refresh-chat', id)
  } else {
    emitter.emit('refresh-chat-list',id)
  }
}
const noPoints = () => {
  emit('no-points')
}
const tabIconStyle = {
  fontSize: '24px',
  color: '#405FFF'
}
const setType = (item, src) => {
  _data.src = src
  _data.activeType = item.type
  // const ProductReplacementRef = ref()
  // const refineRef = ref()
  // const ExtendRef = ref()
  // const EliminateRef = ref()
  // const ColorAdjustmentRef = ref
  if(item.type==='1') ProductReplacementRef.value.init(src)
  if(item.type==='2') refineRef.value.init(src)
  if(item.type==='3') ExtendRef.value.init(src)
  if(item.type==='4') EliminateRef.value.init(src)
  if(item.type==='5') ColorAdjustmentRef.value.init(src)

}
defineExpose({
  setType
})

</script>

<style lang="less" scoped>
.system-group {
  margin: 10px 10px 10px 0;
  // background: @bg-page-two-color;
  background: rgb(25, 25, 27);

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
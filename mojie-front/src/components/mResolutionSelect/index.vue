<template>
  <a-popover placement="top" trigger="click" v-model:visible="visible" color="#121212"
             overlayClassName="m-resolution-select-popover">
    <template #content>
      <div class="modal-select">
        <div class="select-title">生图规格</div>
        <template v-for="(aItem, aIndex) in resolutionList" :key="aIndex">
          <div v-if="aItem.modal.indexOf(userStore.modelType)!==-1" class="item"
            :class="{'cursor': !!aItem.value,active:aItem.value === chatStore.resolutionType}"
               @click="setResolutionType(aItem)">
            <div class="flex items-center">
              <i :class="['iconfont', aItem.icon]"></i>
              <div class="text-box">
                <div class="t1">{{ aItem.label }}</div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </template>
    <div class="m-resolution-select-btn" v-if="currentLabel">
      <div class="flex items-center justify-center">
        <i :class="['iconfont', currentLabel.icon]"></i>
        <div class="text-box">
          {{ currentLabel.label }}
        </div>
      </div>
    </div>
  </a-popover>
</template>

<script setup>
import {computed, ref, watch} from 'vue'
import {useChatStore} from '@/store/chatStore.js';
import {useUserStore} from '@/store/userStore';
import {resolutionList} from '@/options/model.js';

const chatStore = useChatStore();
const userStore = useUserStore();
// 获取当前选中项
const getChoice = () => {
  let res = null;
  for (let i = 0; i < resolutionList.length; i++) {
    let aItem = resolutionList[i];
    if(aItem.modal.indexOf(userStore.modelType)!==-1){
      if (aItem.value === chatStore.resolutionType) {
        res = aItem;
        break
      }
    }
  }
  return res;
}
watch(() => userStore.modelType, (query, oldParams) => {
     if(!getChoice()){
       chatStore.setResolutionType('1:1');
     }
}, {immediate: true});

const visible = ref(false)
const currentLabel = computed(() => {
  return getChoice()
})

// 设置模型类型
const setResolutionType = (item) => {
  chatStore.setResolutionType(item.value);
  visible.value = false
}

</script>

<style lang="less">
.m-resolution-select-popover {
  .ant-popover-inner-content{
    padding: 5px 0;
  }

  .modal-select {
    width: 100px;
    padding: 5px;
    .select-title{
      color: #FFFFFF;
      font-size: 14px;
      padding: 5px;
    }
    .item {
      padding: 4px 5px;
      border-radius: 4px;
      &.cursor {
        cursor: pointer;
        &:not(.active):hover {
          background: #877a7a;
        }
      }

      .t1 {
        font-size: 14px;
        color: #fff;
      }

      .text-box {
        flex: 1;
        width: 0;
        padding: 0 0 0 5px;
      }

      &.active {
        background:@bg-page-two-color;
        .check-icon {
          color: #9B4FFE !important;
        }
      }
    }
  }
  .iconfont {
    font-size: 20px;
    color: #FFFFFF;
  }
}

.m-resolution-select-btn {
  margin-left: 0;
  background: @bg-page-color;
  color: #797979;
  border: 1px solid #2A2A2A;
  width: 60px;
  height: 32px;
  line-height: 32px;
  border-radius: 16px;
  cursor: pointer;
  .iconfont {
    font-size: 20px;
    color: #FFFFFF;
  }
  .text-box {
    padding: 0 0 0 3px;
    font-size: 12px;
    color: #fff;
  }
}
</style>
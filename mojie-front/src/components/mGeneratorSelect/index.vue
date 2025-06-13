<template>
  <a-popover placement="top" trigger="click" v-model:visible="visible" color="#121212"
             overlayClassName="m-generator-select-popover">
    <template #content>
      <div class="modal-select">
        <div class="select-title">生图数量</div>
        <template v-for="(aItem, aIndex) in generatorList" :key="aIndex">
          <div v-if="aItem.show !== false" class="item"
            :class="{'cursor': !!aItem.value,active:aItem.value === chatStore.generatorType}"
               @click="setGeneratorType(aItem)">
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
    <div class="m-generator-select-btn">
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
import {computed, ref} from 'vue'
import {useChatStore} from '@/store/chatStore.js';
import {generatorList} from '@/options/model.js';
const chatStore = useChatStore();

// 当前的label

const visible = ref(false)
const currentLabel = computed(() => {
  return getChoice()
})
// 获取当前选中项
const getChoice = () => {
  let res = null;
  for (let i = 0; i < generatorList.length; i++) {
    let aItem = generatorList[i];
    if (aItem.value === chatStore.generatorType) {
      res = aItem;
      break
    }
  }
  return res;
}

// 设置模型类型
const setGeneratorType = (item) => {
  chatStore.setGeneratorType(item.value);
  visible.value = false
}

</script>

<style lang="less">
.m-generator-select-popover {
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

.m-generator-select-btn {
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
    font-size: 16px;
    color: #FFFFFF;
  }
  .text-box {
    padding: 0 0 0 3px;
    font-size: 12px;
    color: #fff;
  }
}
</style>
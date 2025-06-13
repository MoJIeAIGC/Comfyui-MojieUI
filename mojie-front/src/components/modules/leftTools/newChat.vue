<template>
  <div class="new-box flex flex-col">
    <div class="search-box">
      <a-input class="ipt" v-model:value="_data.searchKey" placeholder="关键字">
        <template #suffix>
          <i class="iconfont icon-fangdajingsousuo"></i>&nbsp;搜索
        </template>
      </a-input>
    </div>
    <div class="add-btn" @click="showAddChat">
      <span>开启新对话</span>
    </div>
    <div class="list flex-1 h-0-o-a">
      <!--          <div class="list-time">今天</div>-->
      <template v-for="(item, index) in _data.sessionList" :key="index">
        <div
            v-if="!_data.searchKey|| item.name.indexOf(_data.searchKey)!=-1"
            class="item"
            :class="{active: item.id === props.chatId}"
            :title="item.name"
            @click="choiceSession(item)">
          <div class="text-box line1">
            <span>{{ item.name || '会话' + index }}</span>
          </div>
          <div class="right-box line1">
            <DeleteFilled @click.stop="deleteSession(item)"/>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import {watch,defineEmits, reactive, createVNode, defineProps, onMounted, onUnmounted} from 'vue'
import {notification, Modal} from "ant-design-vue";
import emitter from '@/utils/emitter'
import {useUserStore} from '@/store/userStore.js';
import {
  DeleteFilled,
  ExclamationCircleOutlined,
} from "@ant-design/icons-vue";
import {delNewConver, getNewConver} from "@/api/chat.js";

const userStore = useUserStore();
const emit = defineEmits(['change']);
const _data = reactive({
  searchKey: '',
  sessionList: []
})
onMounted(() => {
  emitter.on('refresh-chat', (chatId) => {
    _data.searchKey = ''
    emit('change', chatId)
    getSessions({id: chatId})
  });
})

onUnmounted(() => {
  emitter.off('refresh-list')
})
// 当前的label
// watch(() => userStore.modelType, (query, oldParams) => {
//   showAddChat()
// });
const props = defineProps({
  chatId: {
    type: Number,
    default: -1
  }
})

// 新建会话
function showAddChat() {
  emit('change', -1)
}

// 删除会话
function deleteSession(item, index) {
  let formData = new FormData()
  formData.append('id', item.id)
  Modal.confirm({
    title: '提示',
    icon: createVNode(ExclamationCircleOutlined),
    content: `确定删除会话《${item.name}》么`,
    onOk() {
      delNewConver(formData).then((res) => {
        notification.success({
          message: '提示',
          description: '删除成功'
        });
        if (props.chatId === item.id) {
          getSessions();
        } else {
          _data.sessionList.splice(index, 1);
        }
      })
    },
    onCancel() {
    },
  });
}

getSessions()

// 获取会话列表
function getSessions(item, flag) {
  getNewConver(userStore.userinfo.userId).then(res => {
    _data.sessionList = res.data
    let _id = -1
    if (item && item.id) {
      _id = item.id
    } else {
      if(props.chatId ===-1) {
        _id = res.data && res.data.length > 0 ? res.data[0].id : -1
      } else {
        _id = props.chatId
      }
    }
    if (!flag) emit('change', _id)
  })
}

// 选中会话
function choiceSession(item, isLoad = false) {
  if (props.chatId === item.id && !isLoad) {
    return;
  }
  emit('change', item.id)
}

const refreshList = (item) => {
  getSessions(item, true)
}
defineExpose({
  refreshList
})
</script>

<style lang="less" scoped>
.new-box {
  height: 100%;
  padding: 10px;

  .search-box {
    padding: 15px 0;

    .ipt {
      padding: 5px 20px;
      border-radius: 20px;
      width: 340px;
      height: 37px;
      background-color: #222325;
      border-color: #222325;
      font-size: 14px;

      :deep(.ant-input) {
        background-color: inherit;
      }

      .iconfont {
        font-size: 18px;
      }
    }
  }
  .ipt:hover {
  border-color: #3557FF; /* 悬停时边框变为蓝色 */
  transition: border-color 0.3s ease; /* 添加过渡效果 */
  box-shadow: 0 0 0 2px rgba(53, 87, 255, 0.2); /* 添加蓝色光晕效果 */
}

  .add-btn {
    margin: 15px 0 30px;
    padding: 0 10px;
    height: 32px;
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    cursor: pointer;
    background: @btn-bg-two-color;

    &:hover {
      opacity: 0.8;
    }
  }

  .list {
    color: #ffffff;

    .list-time {
      padding: 5px 25px;
      height: 44px;
      display: flex;
      align-items: center;
      color: #999999;
    }

    .item {
      padding: 0 10px;
      height: 44px;
      display: flex;
      align-items: center;
      cursor: pointer;

      &.active, &:hover {
        background: #1A1E35;
        border-radius: 8px;
      }

      .text-box {
        margin: 0 10px;
        width: 0;
        flex: 1;
        color: #fff;
      }

      .right-box {
        width: 20px;
        display: flex;
        justify-content: space-between;

        .icon {
          font-size: 15px;
          cursor: pointer;
          color: #fff;
        }
      }
    }
  }
}
</style>
<template>
  <div class="new-box flex flex-col">
    <div class="search-box">
      <a-input class="ipt" v-model:value="_data.searchKey" placeholder="关键字">
        <template #suffix>
          <i class="iconfont icon-fangdajingsousuo"></i>&nbsp;搜索
        </template>
      </a-input>
    </div>
    <div class="list flex-1 h-0-o-a">
      <!--          <div class="list-time">今天</div>-->
      <template v-for="(item, index) in _data.sessionList" :key="index">
        <div
            v-if="!_data.searchKey|| item.video_name.indexOf(_data.searchKey)!=-1"
            class="item"
            :class="{active: item.id === props.videoId}"
            :title="item.video_name"
            @click="choiceSession(item)">
          <div class="text-box line1">
            <span>{{ item.video_name || '生成视频记录' + index }}</span>
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
import {defineEmits, reactive, createVNode, onMounted, onUnmounted, defineProps} from 'vue'
import {notification, Modal} from "ant-design-vue";
import {
  DeleteFilled,
  ExclamationCircleOutlined,
} from "@ant-design/icons-vue";
import {delVideos, getVideos} from "@/api/video.js";

const emit = defineEmits(['change']);
const _data = reactive({
  searchKey: '',
  sessionList: []
})
const props = defineProps({
  videoId: {
    type: Number,
    default: -1
  }
})
onMounted(() => {
  // emitter.on('refresh-chat', (chatId) => {
  //   emit('change', chatId)
  // });
})

onUnmounted(() => {
  //emitter.off('refresh-list')
})
// 删除会话
function deleteSession(item, index) {
  Modal.confirm({
    title: '提示',
    icon: createVNode(ExclamationCircleOutlined),
    content: `确定删除视频记录《${item.video_name}》么`,
    onOk() {
      delVideos(item.id).then((res) => {
        notification.success({
          message: '提示',
          description: '删除成功'
        });
        getVideoList('del',item.id);
      })
    },
    onCancel() {
    },
  });
}

getVideoList()

// 获取会话列表
function getVideoList(id, flag) {
  getVideos().then(res => {
    _data.sessionList = res.data
    if(id==='del'&&props.videoId !== flag) return
    let _id = -1
    if (id && id!=='del') {
      _id = id
    } else {
      if(props.videoId ===-1||id==='del') {
        _id = res.data && res.data.length > 0 ? res.data[0].id : -1
      } else {
        _id = props.videoId
      }
    }
    if (!flag || id==='del') emit('change', _id)
  })
}

// 选中会话
function choiceSession(item) {
  if (props.videoId === item.id) return;
  emit('change', item.id)
}

const refreshList = (id) => {
  getVideoList(id, true)
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
      height: 30px;
      background-color: inherit;
      border-color: #2F3034;
      font-size: 14px;

      :deep(.ant-input) {
        background-color: inherit;
      }

      .iconfont {
        font-size: 18px;
      }
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
<template>
  <div class="home-wp">
    <leftMenu ref="leftMenuRef" @change="chatChange"/>
    <div class="center">
      <a-spin tip="生成中，请等待..." :spinning="_data.loading">
        <div class="posct view-layer-result">
          <video ref="videoRef" :src="_data.url" controls
                 @pause="handlePause"
                 @ended="handleEnded"
                 @play="handlePlay" >
            您的浏览器不支持 video 标签。
          </video>
          <caret-right-outlined class="play" v-if="!playFlag&&_data.url" :style="iconStyle"
                                @click.stop="videoPauseOrPlay"/>
        </div>

      </a-spin>
    </div>
    <rightTool ref="rightToolRef" @change="change"></rightTool>
  </div>
</template>

<script setup>
import {reactive, ref, onMounted, onUnmounted} from 'vue'
import {
  CaretRightOutlined,
} from '@ant-design/icons-vue';
import rightTool from "@/components/videoModules/rightTool.vue";
import leftMenu from "@/components/videoModules/leftMenu.vue"
import {getVideoStatus} from "@/api/video.js";

const rightToolRef = ref();
const leftMenuRef = ref();
const _data = reactive({
  loading: false,
  url: '',
  generationInfo: {},
  timer: null
})
onMounted(() => {

})

onUnmounted(() => {
  if( _data.timer) clearTimeout(_data.timer);
})
const playFlag = ref(false)
const videoRef = ref()
const iconStyle = {
  color: '#fff'
}
const chatChange = (id) => {
  if(id===-1) return
  _data.loading = true
  _data.generationInfo = {}
  _data.url = ''
  refreshVideo(id)
}
//暂停或播放
const videoPauseOrPlay = () => {
  if (!_data.url) return
  if (playFlag.value) {
    videoRef.value.pause();
  } else {
    videoRef.value.play();
  }
}
//视频暂停了
const handlePause = () => {
  playFlag.value = false
};
const handlePlay = () => {
  playFlag.value = true
};
//视频播放结束了
const handleEnded = () => {
  playFlag.value = false
};
//视频播放结束了
const change = (info) => {
  if( _data.timer) clearTimeout(_data.timer);
  _data.loading = true
  _data.generationInfo = {}
  _data.url = ''
  leftMenuRef.value.changeVideo(info.video_record_id)
  refreshVideo(info.video_record_id)
};//视频播放结束了
const refreshVideo = (id) => {
  getVideoStatus(id).then(res => {
   const _d = res.data
    if(_d&&_d.task_status==='completed'){
      _data.generationInfo = _d
      _data.url = _d.video_address
      if( _data.timer) clearTimeout(_data.timer);
      _data.loading = false
      return
    }
    _data.timer = setTimeout(() => {
       if( _data.timer) clearTimeout(_data.timer);
       refreshVideo(id)
    },5000)
  })
};
</script>

<style lang="less" scoped>
.home-wp {
  height: 100%;
  display: flex;

  .center {
    position: relative;
    width: 0;
    flex: 1;
    background-color: @bg-page-color;
    padding: 10px;

    .view-layer-result {
      //padding: 40px;
      height: calc(100vh - 240px);
      width: 100%;
      position: relative;

      video {
        border-radius: 5px;
        height: 100%;
        width: 100%;
      }

      .play {
        font-size: 90px;
        position: absolute;
        top: calc(50% - 45px);
        left: calc(50% - 45px);
        cursor: pointer;
      }
    }
  }
}
</style>
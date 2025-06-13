<template>
  <a-modal class="share-modal" v-model:visible="_data.visible" @cancel="cancel" :footer="null" width="80vw">
    <div slot="title"></div>
    <div class="member-content">
      <div class="posct view-layer-result">
        <!--               controlslist="nodownload nofullscreen noremoteplayback"-->
<!--        @click.stop="videoPauseOrPlay"-->
        <video ref="videoRef" :src="_data.url" controls
               @pause="handlePause"
               @ended="handleEnded"
               @play="handlePlay"
               @contextmenu="contextmenu">
                您的浏览器不支持 video 标签。
        </video>
        <caret-right-outlined  class="play" v-if="!playFlag&&_data.url" :style="iconStyle" @click.stop="videoPauseOrPlay" />
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { reactive,ref} from 'vue'
import {CaretRightOutlined} from '@ant-design/icons-vue';
const playFlag = ref(false)
const videoRef = ref()
const _data = reactive({
  visible: false,
  //url:'blob:https://www.bilibili.com/0edabcbc-97c3-4a24-8346-68cf3a05b20e'
  url:'https://qihuaimage.tos-cn-guangzhou.volces.com/static/%E8%BF%81%E7%A7%BB%E6%9B%BF%E6%8D%A2.mp4'
  // url:'https://www.runoob.com/try/demo_source/movie.mp4'
})
const iconStyle = {
  color: '#fff'
}
//禁止右键行为
const contextmenu = (e) => {
  e.returnValue = false
}
//暂停或播放
const videoPauseOrPlay = () => {
  if(!_data.url) return
  if (playFlag.value) {
    videoRef.value.pause();
  } else {
    videoRef.value.play();
  }
}
//视频暂停了
const handlePause = () => {
  playFlag.value=false
};
const handlePlay = () => {
  playFlag.value=true
};
//视频播放结束了
const handleEnded = () => {
   playFlag.value=false
};
const cancel = () => {
 if(videoRef.value) videoRef.value.pause();
}
function open(url) {
  _data.visible = true
   //_data.url = url
}
defineExpose({
  open
})

</script>

<style lang="less" scoped>
.member-content {
  border-radius: 16px;
  padding:20px;
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
</style>
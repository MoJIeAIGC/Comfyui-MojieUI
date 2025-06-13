<template>
  <div class="flex flex-col">
    <div class="flex-1 h-0-o-a">
      <div class="header-img">
        <div class="image-view flex justify-center items-center" :class="drapClass" v-if="!_data.videoUrlBlob"
             @drop.prevent="handleDrop" @dragover.prevent="drapClassChange('over')"
             @dragenter.prevent="drapClassChange('enter')" @dragleave="drapClassChange('leave')">
          <div v-if="!_data.videoUrlBlob" class="up-btn flex items-center justify-center" @click="uploadFile">
            <div class="text-center">
              <PlusOutlined :style="{fontSize: '26px'}"/>
              <div class="ant-upload-file-tips">添加视频(支持拖拽添加)</div>
            </div>
          </div>
        </div>
        <close-circle-filled class="close-img" v-if="_data.videoUrlBlob" @click="clearVideo"/>
        <div class="flex items-center justify-center" :class="drapClass" v-if="_data.videoUrlBlob"
             @drop.prevent="handleDrop" @dragover.prevent="drapClassChange('over')"
             @dragenter.prevent="drapClassChange('enter')" @dragleave="drapClassChange('leave')">
          <div class="posct view-layer-result">
            <!--               controlslist="nodownload nofullscreen noremoteplayback"-->
            <!--        @click.stop="videoPauseOrPlay"-->
            <video ref="videoRef" :src="_data.videoUrlBlob" controls>
              您的浏览器不支持 video 标签。
            </video>
          </div>
        </div>
      </div>
      <div class="audio-box">
        <div class="audio-view flex justify-center items-center"  v-if="!_data.audioUrlBlob">
          <div v-if="!_data.audioUrlBlob" class="up-btn flex items-center justify-center" @click="uploadAudioFile">
            <div class="text-center">
              <PlusOutlined :style="{fontSize: '26px'}"/>
              <div class="ant-upload-file-tips">添加音频</div>
            </div>
          </div>
        </div>
        <close-circle-filled class="close-img" v-if="_data.audioUrlBlob" @click="clearAudio"/>
        <div class="flex items-center justify-center" v-if="_data.audioUrlBlob">
          <div class="posct view-layer-result">
            <audio ref="audioRef" :src="_data.audioUrlBlob" controls @loadedmetadata="loadAudio">
              您的浏览器不支持 audio 标签。
            </audio>
          </div>
        </div>
      </div>
    </div>
    <div class="bottom-btn">
      <a-button type="primary" size="large" shape="round" class="send-btn items-center justify-center" :disabled="isDis"
                @click="saveImage" :loading="_data.loading">
        <template #icon>
          <i class="iconfont icon-a-ziyuan19"></i>
        </template>
        立即生成（{{ pointText }}）
      </a-button>
    </div>
  </div>
</template>
<script setup>
import {reactive, ref, nextTick, defineEmits, computed, defineExpose, onUnmounted} from "vue";
import {CaretRightOutlined, CloseCircleFilled, PlusOutlined} from "@ant-design/icons-vue";
import {isVideoFile} from "@/utils/utils.js";
import {message} from "ant-design-vue";
import {postVideoGeneration} from "@/api/video.js";
import {postUploadVideo} from "@/api/upload.js";
import {deductionRules} from "@/options/model.js";
import {useUserStore} from "@/store/userStore.js";
const userStore = useUserStore()
const emit = defineEmits(['change']);
const videoRef = ref()
const audioRef = ref()
const _deductionRules = computed(() => {
  const isVip = userStore.vipInfo && userStore.vipInfo.level
  return isVip ? deductionRules.vip : deductionRules.default
});
const pointText = computed(() => {
  const isVip = userStore.vipInfo && userStore.vipInfo.level
  if (_deductionRules.value.video === 0 && isVip) return '会员免费'
  return '消耗' + _deductionRules.value.video + '算力'
});
const _data = reactive({
  loading: false,
  audioUrl: '',
  audioUrlBlob: '',
  videoUrlBlob: '',
  videoUrl: ''
})
onUnmounted(() => {
  if (_data.timer2) clearTimeout(_data.timer2);
})
const drapClass = ref('')
const drapClassChange = (type) => {
  drapClass.value = type
}
const handleDrop = (event) => {
  drapClass.value = ''
  let url = event.dataTransfer.getData('text/plain'); // 获取数据
  if (url) {
    message.warning("暂不支持拖入链接")
    _data.videoUrl = url
    return;
  }
  const files = event.dataTransfer.files;
  if (files.length > 1) return message.warning("只能拖入一个视频文件")
  if (files.length === 1) {
    if (isVideoFile(files[0].type)) {
      if(files[0].size> 50*1204*1024){
        message.error('上传视频不能超过50M')
        return
      }
      clearVideo()
      uploadVideo(files[0], 'video')
    } else {
      message.warning("拖入的文件不是视频格式")
    }
  }
}
const isDis = computed(() => {
  if (_data.loading) return _data.loading
  // if(!_data.optImage||!_data.optImage.image_url) return true
  return false
});
const init = (src) => {
  nextTick(() => {
  })
}

const uploadVideo = async (file, type) => {
  return new Promise((resolve) => {
    const fileData = new FormData();
    fileData.append('file', file)
    postUploadVideo(fileData).then(result => {
      if (type === 'video') {
        _data.videoUrl = result.data.data.fileName
        _data.videoUrlBlob = URL.createObjectURL(file)
      }
      if (type === 'audio') {
        _data.audioUrl = result.data.data.fileName
        _data.audioUrlBlob = URL.createObjectURL(file)
      }
      resolve()
    }, err => {
      resolve()
    })
  })
};
const uploadFile = () => {
  let fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = "video/*";
  fileInput.click();
  fileInput.onchange = (event) => {
    if(event.target.files[0].size> 50*1204*1024){
      message.error('上传视频不能超过50M')
      return
    }
    uploadVideo(event.target.files[0], 'video')
  }
}
const uploadAudioFile = () => {
  let fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = "audio/*";
  fileInput.click();
  fileInput.onchange = (event) => {
    if(event.target.files[0].size> 10*1204*1024){
      message.error('上传音频不能超过10M')
      return
    }
    uploadVideo(event.target.files[0], 'audio')
  }
}
const saveImage = async () => {
  _data.loading = true
  let res = await postVideoGeneration(_data.videoUrl, _data.audioUrl)
  emit('change', res.data)
  _data.timer2 = setTimeout(() => {
    _data.loading = false
  }, 15 * 1000)
}
const loadAudio = (event) => {
  console.log(event.target.duration)
}
const clearVideo = () => {
  _data.videoUrl = ''
  _data.videoUrlBlob = ''
}
const clearAudio = () => {
  _data.audioUrl = ''
  _data.audioUrlBlob = ''
}
defineExpose({
  init
})
</script>

<style scoped lang="less">
.flex-col {
  height: 100%;
}

.header-img {
  position: relative;
  padding: 30px 10px 15px;

  .close-img {
    position: absolute;
    top: 20px;
    right: 0;
    z-index: 99;
  }

  .image-view {
    width: 100%;
    height: 220px;
    background: @bg-page-color;
    border-radius: 8px;
    position: relative;

    &:hover {
      background: @bg-page-hover-color;
    }

    .up-btn {
      padding: 10px 5px;
      width: 100%;
      height: 200px;
      cursor: pointer;

      .ant-upload-file-tips {
        font-size: 12px;
      }
    }

    .close-img {
      font-size: 20px;
      position: absolute;
      top: -10px;
      right: -10px;
      color: #999999;
      z-index: 99;
      cursor: pointer;
    }
  }

  .view-layer-result {
    //padding: 40px;
    width: 100%;
    position: relative;

    video {
      border-radius: 5px;
      height: 220px;
      width: 100%;
    }
  }

  .over {
    background: @bg-page-hover-color;
  }
}
.audio-box {
  position: relative;
  padding: 30px 10px 15px;

  .close-img {
    position: absolute;
    top: 20px;
    right: 0;
    z-index: 99;
  }

  .audio-view {
    width: 100%;
    height: 120px;
    background: @bg-page-color;
    border-radius: 8px;
    position: relative;

    &:hover {
      background: @bg-page-hover-color;
    }

    .up-btn {
      padding: 10px 5px;
      width: 100%;
      height: 200px;
      cursor: pointer;
      .ant-upload-file-tips {
        font-size: 12px;
      }
    }

    .close-img {
      font-size: 20px;
      position: absolute;
      top: -10px;
      right: -10px;
      color: #999999;
      z-index: 99;
      cursor: pointer;
    }
  }

  .view-layer-result {
    //padding: 40px;
    width: 100%;
    position: relative;
    audio {
      width: 100%;
    }
  }
}

.collapse-box {
  margin: 10px;
  padding: 10px 15px;
  border-radius: 8px;
  background-color: @bg-page-color;

  > .flex {
    margin-bottom: 10px;
  }

  .left-title {
    line-height: 30px;
    font-size: 13px;
    width: 60px;
    color: #FFFFFF;
  }

  .painting-item {
    margin-left: 10px;
  }
}

.bottom-btn {
  margin: 15px 10px 30px;
  height: 40px;

  .send-btn {
    width: 100%;
    display: flex;
    font-size: 14px;
    cursor: pointer;
    color: #fff;
    border: 0;
    background: @btn-bg-color;

    .iconfont {
      fill: #FFFFFF;
      font-size: 14px;
      margin-right: 5px
    }

    &[disabled] {
      cursor: not-allowed !important;
    }

    &:hover {
      opacity: 0.8;
    }
  }
}
</style>
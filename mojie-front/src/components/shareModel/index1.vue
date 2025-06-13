<template>
  <a-modal class="vip-modal" v-model:visible="_data.visible" :maskClosable="false" :footer="null" width="450px">
    <div slot="title"></div>
    <div class="member-content">
        <div class="title text-center">
          <div class="h5">分享</div>
        </div>
        <div class="share-code flex">
          <div class="share-img">
            <qrcode-vue id="qrcode-ref" ref="qrcodeRef" :value="_data.url" :margin="1" :size="400" level="H" :image-settings="_data.imageSettings"></qrcode-vue>
          </div>
        </div>
        <div> <a-button type="link" size="small" @click="downImage">下载</a-button>分享码或<a-button type="link" size="small" @click="copyUrl"> 复制</a-button>链接分享(长期有效)</div>
    </div>
  </a-modal>
</template>

<script setup>
import { reactive,ref} from 'vue'
import {message} from "ant-design-vue";
import {queryUserShareCode} from "@/api/login.js";
import QrcodeVue from 'qrcode.vue';
import logo from '@/assets/image/logo.png';
import {canvasTobase64, handleDownloadQrIMg} from "@/utils/utils.js";
const _data = reactive({
  visible: false,
  share_code: '',
  url:'',
  base64: '',
  imageSettings:{
    src: logo,
    width: 80,
    height: 80,
    excavate: true
  }
})
const qrcodeRef = ref()
const initList = () => {
  queryUserShareCode().then(res => {
    _data.url = window.location.origin + '/home?shareCode='+ res.data.share_code
    _data.share_code = res.data.share_code
  })
}
const downImage = () => {
      const canvas = document.getElementById('qrcode-ref');
     _data.base64 =  canvasTobase64(canvas)
     handleDownloadQrIMg(_data.base64,'分享二维码')
}
const copyUrl = () => {
  try {
    const textarea = document.createElement("textarea");
    textarea.value =  '奇画AI邀请您体验AI生图,点击链接体验：' + _data.url + '，邀请码:' + _data.share_code;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
    message.success('复制链接成功')
  } catch (error) {
    console.error(error);
    message.error('复制链接失败')
  }
}
function open() {
  _data.url = window.location.origin
  initList()
  _data.visible = true;
}
defineExpose({
  open
})

</script>

<style lang="less" scoped>
.member-content {
  padding:0;
  .title {
    padding: 0 0 15px;
    .h5 {
      font-size: 32px;
      color: transparent;
      background-clip: text;
      background-image: linear-gradient(to right, #00D1FE, #008AFE, #00D1FE);
    }
  }
  .share-code{
    //background: #FFFFFF;
    canvas{
      border-radius: 8px;
    }
  }
}
</style>
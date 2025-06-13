<template>
  <div>
    <div class="image-content">
      <div class="image-view flex justify-center items-center" :class="[drapClass,{up:!imageUrl}]">
        <div v-if="!imageUrl" class="up-btn flex items-center justify-center" @click="uploadFile"  @drop.prevent="handleDrop" @dragover.prevent="drapClassChange('over')"  @dragenter.prevent="drapClassChange('enter')" @dragleave="drapClassChange('leave')">
          <div class="text-center">
            <PlusOutlined :style="{fontSize: '26px'}"/>
            <div class="ant-upload-file-tips">添加图片(支持拖拽添加)</div>
          </div>
        </div>
        <close-circle-filled class="close-img" v-if="imageUrl" @click="clearImage" />
        <img v-if="imageUrl" :src="imageUrl" @drop.prevent="handleDrop" @dragover.prevent="drapClassChange('over')"  @dragenter.prevent="drapClassChange('enter')" @dragleave="drapClassChange('leave')" alt="">
      </div>
      <div class="flex image-btn" :class="{hasReplace: props.type!=='replace'}">
        <a-tooltip placement="bottom">
          <template #title>
            <span>遮罩画笔</span>
          </template>
          <div class="flex-1" @click="imageFabricShow('draw')">
            <i class="iconfont icon-huabi1" :class="{disabled:!imageUrl }"></i><br>
          </div>
        </a-tooltip>
        <a-tooltip placement="bottom">
          <template #title>
            <span>裁剪</span>
          </template>
          <div class="flex-1" @click="clip" v-if="props.type!=='replace'">
            <i class="iconfont icon-caijian1" :class="{disabled:!imageUrl }"></i><br>
          </div>
        </a-tooltip>
        <a-tooltip placement="bottom">
          <template #title>
            <span>重置</span>
          </template>
          <div class="flex-1" @click="reset()">
            <i class="iconfont icon-zhongzhi3" :class="{disabled:!imageUrl }"></i><br>
          </div>
        </a-tooltip>
      </div>
    </div>
    <ImageFabric :type="props.type" v-bind="_data.options" ref="ImageFabricRef" @change="imageUrlClip"></ImageFabric>
  </div>
</template>
<script setup>
import ImageFabric from '@/components/imageEdit/fabricOrClip.vue'
import {reactive, ref, defineProps, defineEmits, defineExpose} from "vue";
import {PlusOutlined,CloseCircleFilled} from "@ant-design/icons-vue";
import {base64UrlToFile, compressFile, convertImgToBase64, isHttp, isImageFile} from "@/utils/utils.js";
import {message} from "ant-design-vue";
import {httpIndex} from "@/options/model.js";

const imageUrl = ref('')
const initUrl = ref('')
const maskUrl = ref('')
const ImageFabricRef = ref()
const emit = defineEmits(['change']);
const _data = reactive({
  isDrawing: false,
  clipOpen: false,
  options:{}
})
const props = defineProps({
  type: {
    type:String,
    default:''
  }
})
const drapClass = ref('')
const drapClassChange = (type) => {
  drapClass.value = type
}
const handleDrop = (event) =>{
  drapClass.value = ''
  let url = event.dataTransfer.getData('text/plain'); // 获取数据
  if(url){
    if(isHttp(url) &&url.indexOf(httpIndex)===-1){
      message.error('您拖拽的图片链接非本网站的链接，请先下载后再拖入下载后的图片')
      return
    }
    clearImage()
    initSrc(url)
    return;
  }
  const files = event.dataTransfer.files;
  if(files.length>1) return message.warning("只能拖入一个文件")
  if(files.length===1){
    if(isImageFile(files[0].type)){
      clearImage()
      previewFile(files[0])
    } else {
      message.warning("拖入的文件不是图片格式")
    }
  }
}
const clip = (url,type) => {
  if(props.type==='pro'){
    _data.options = {
      // aspectRatio: 1024/1280,
      // outputWidth: 1024,
      // outputHeight: 1280
    }
  } else {
    _data.options = {}
  }
  if(imageUrl.value){
    ImageFabricRef.value.showClip(initUrl.value ? initUrl.value : imageUrl.value,'clip')
  }
  if (type === 'init'){
    ImageFabricRef.value.showClip(url,'clip','init')
  }
}
const imageUrlClip = (url,iUrl,mUrl,isDraw,aaabase) => {
  imageUrl.value = url
  initUrl.value = iUrl
  maskUrl.value = mUrl
  maskUrl.isDrawing = isDraw
  emit('change', props.type==='replace' ? iUrl:url,props.type,mUrl,isDraw,aaabase)
}
const previewFile = file => {
  if (file.size > 3 * 1024 * 1024) {
    compressFile(file, (newFile) => {
      fileToBase64(newFile)
    })
  } else {
    fileToBase64(file)
  }
  return false
}
const uploadFile = () => {
  let fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = "image/*";
  fileInput.click();
  fileInput.onchange = (event)=>{
    previewFile(event.target.files[0])
  }
}
const fileToBase64 = file => {
  let r = new FileReader();
  r.readAsDataURL(file);
  r.onload = () => { // 读取操作完成回调方法
    // that.$refs.canvas.upLoadImage(r.result);
    // if(props.type === 'pro'){
    //   imageUrl.value = ''
    //   clip(r.result,'init')
    // } else {
      imageUrl.value = r.result
      emit('change', imageUrl.value,props.type,'upload')
    // }
  };
  return false
}

const imageFabricShow = (type) => {
  if(imageUrl.value){
    ImageFabricRef.value.showClip(initUrl.value ? initUrl.value : imageUrl.value, type,'')
  }
}
const reset = () => {
  if(imageUrl.value){
    ImageFabricRef.value.resetToParent()
  }
}
const clearImage = () => {
  imageUrl.value = ''
  initUrl.value = ''
  ImageFabricRef.value.clearHistoryList()
  emit('change', 'clear',props.type)
}
const cancel = () => {
  ImageFabricRef.value.cancel()
}
const initSrc = (src) => {
  convertImgToBase64(src,(base64)=>{
    clearImage()
    const draFile = base64UrlToFile(base64)
    previewFile(draFile)
  })
}

defineExpose({
  cancel,
  initSrc
})
</script>
<style scoped lang="less">
.image-content {
  //background: #31373D;
  border-radius: 8px;

  .image-view {
    width: 100%;
    height: 220px;
    background: @bg-page-color;
    border-radius: 8px;
    position: relative;
    .up-btn {
      padding: 10px 5px;
      width: 100%;
      height: 200px;
      cursor: pointer;
      .ant-upload-file-tips{
        font-size: 12px;
      }
    }
    &.up:hover ,&.over{
      background: @bg-page-hover-color;
    }
    .close-img{
       font-size: 20px;
       position: absolute;
       top: -10px;
       right: -10px;
      color: #999999;
      z-index: 99;
      cursor: pointer;
    }
    img{
      max-width: 100%;
      max-height: 100%;
    }
  }
  .image-btn{
     margin:10px 45px 0;
     padding:5px;
     height: 30px;
     font-size: 12px;
     text-align: center;
     color: #787878;
    border-radius: 20px;
    background-color: #303030;
    &.hasReplace{
      margin:10px 30px 0;
    }
    >.flex-1{
      line-height: 20px;
      .iconfont{
        cursor: pointer;
        font-size: 18px;
        &.disabled{
          &.disabled{
            color: #5e5959;
          }
        }
      }
    }
    //.flex-1:nth-child(n+2){
    //
    //   border-left: 1px solid #383E44;
    //}
  }
}
</style>
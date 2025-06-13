<template>
  <div class="flex flex-col">
    <div class="flex-1 h-0-o-a">
      <div class="header-img">
        <div class="image-view flex justify-center items-center" :class="drapClass" v-if="!_data.url" @drop.prevent="handleDrop" @dragover.prevent="drapClassChange('over')"  @dragenter.prevent="drapClassChange('enter')" @dragleave="drapClassChange('leave')">
          <div v-if="!_data.url" class="up-btn flex items-center justify-center" @click="uploadFile">
            <div class="text-center">
              <PlusOutlined :style="{fontSize: '26px'}"/>
              <div class="ant-upload-file-tips">添加图片(支持拖拽添加)</div>
            </div>
          </div>
        </div>
        <close-circle-filled class="close-img" v-if="_data.url" @click="clearImage" />
        <div class="flex items-center justify-center" :class="drapClass" v-if="_data.url" @drop.prevent="handleDrop" @dragover.prevent="drapClassChange('over')"  @dragenter.prevent="drapClassChange('enter')" @dragleave="drapClassChange('leave')">
          <img alt="" :src="_data.edtUrl">
        </div>
        <div id="canvas-glfx"></div>
      </div>
      <div class="collapse-box">
        <div class="flex">
          <div class="left-title">亮度</div>
          <div class="text-center painting-item flex-1 slider-dot-customize">
            <a-slider v-model:value="_data.brightness" :max="200" :marks="marks" @change="change"></a-slider>
          </div>
        </div>
        <div class="flex">
          <div class="left-title">对比度</div>
          <div class="text-center painting-item flex-1 slider-dot-customize">
            <a-slider v-model:value="_data.contrast" :max="200" :marks="marks" @change="change"></a-slider>
          </div>
        </div>
        <div class="flex">
          <div class="left-title">饱和度</div>
          <div class="text-center painting-item flex-1 slider-dot-customize">
            <a-slider v-model:value="_data.saturate" :max="200" :marks="marks" @change="change"></a-slider>
          </div>
        </div>
<!--        <div class="flex">-->
<!--          <div class="left-title">锐化</div>-->
<!--          <div class="text-center painting-item flex-1 slider-dot-customize">-->
<!--            <a-slider v-model:value="_data.sharpening" :max="200" :marks="marks" @change="change"></a-slider>-->
<!--          </div>-->
<!--        </div>-->
<!--        <div class="flex">-->
<!--          <div class="left-title">噪点</div>-->
<!--          <div class="text-center painting-item flex-1 slider-dot-customize">-->
<!--            <a-slider v-model:value="_data.noise" :max="200" :marks="marks" @change="change"></a-slider>-->
<!--          </div>-->
<!--        </div>-->
      </div>
    </div>
    <div class="bottom-btn">
      <a-button type="primary" size="large" shape="round" class="send-btn items-center justify-center" :disabled="isDis" @click="saveImage" :loading="_data.loading">
        <template #icon>
          <i class="iconfont icon-a-ziyuan19"></i>
        </template>
        保存
      </a-button>
    </div>
  </div>
</template>
<script setup>
import {reactive, ref, nextTick, defineProps, watch, defineEmits, computed, defineExpose, onUnmounted} from "vue";
import {CloseCircleFilled, PlusOutlined} from "@ant-design/icons-vue";
import {colorAdjustment} from "@/api/product.js";
import {base64UrlToFile, convertImgToBase64, isImageFile,compressFile} from "@/utils/utils.js";
import {uploadImg} from "@/api/upload.js";
import {useUserStore} from "@/store/userStore.js";
import {message} from "ant-design-vue";
const userStore = useUserStore()
let canvas = null
let texture = null
const emit = defineEmits(['change']);
// let imageUrl = ''
const props = defineProps({
  chatId: {
    type:[String,Number],
    default:''
  }
})
const _data = reactive({
  loading:false,
  image:{},
  optImage:{},
  brightness: 100,
  contrast: 100,
  saturate: 100,
  hue: 100,
  noise: 0,
  sharpening: 0,
  url: props.src,
  timer2: null,
  edtUrl: ''
})
onUnmounted(() => {
  if( _data.timer2) clearTimeout(_data.timer2);
})
const drapClass = ref('')
const drapClassChange = (type) => {
  drapClass.value = type
}
const handleDrop = (event) =>{
  drapClass.value = ''
  let url = event.dataTransfer.getData('text/plain'); // 获取数据
  if(url){
    convertImgToBase64(url,(base64)=>{
      clearImage()
      const draFile = base64UrlToFile(base64)
      previewFile(draFile)
    })
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
const isDis = computed(() => {
  if(_data.loading) return _data.loading
  // if(!_data.optImage||!_data.optImage.image_url) return true
  return false
});
const marks = ref({
  0: '0%',
  50: '50%',
  100: '100%',
  150: '150%',
  200: '200%',
});
const init = (src) => {
  if(src) _data.url = src
  nextTick(()=>{
    canvas = fx.canvas();
    canvas.id = 'save-canvas';
    const image = new Image();
    image.onload = ()=>{
      texture = canvas.texture(image);
      canvas.draw(texture)
      canvas.update()
      // document.getElementById('canvas-glfx').appendChild(canvas)
      _data.edtUrl = canvas.toDataURL('image/png');
      //texture.destroy()
    }
    _data.edtUrl = _data.url
    image.src = _data.url
    image.crossOrigin = "Anonymous"
  })
}

const saveImage = async () => {
  const imgFile = base64UrlToFile(_data.url)
  const maskFile = base64UrlToFile(_data.edtUrl)
  await uploadImage(imgFile,'start')
  await uploadImage(maskFile,'mask')
  const sub_data = {
    description: `色彩调节，亮度${_data.brightness}，对比度${_data.contrast}，饱和度${_data.saturate}`,
    add_new_data:JSON.stringify({
      text:`色彩调节，亮度${_data.brightness}，对比度${_data.contrast}，饱和度${_data.saturate}`,
      type:'color',
    }),
    conversation_id: !props.chatId || props.chatId===-1||props.chatId==='-1'?'':props.chatId,
    input_image_url: _data.image.image_url,
    output_image_url: _data.optImage.image_url
  }
  _data.loading= true
  let res = await colorAdjustment(sub_data)
  emit('change', {sendInfo: 'color',res: res.data},res.data.conversation_id)
  _data.timer2 = setTimeout(()=>{
    _data.loading= false
  },15 * 1000)
}
const uploadImage = async (file, type) => {
  return new Promise((resolve, reject) => {
    const fileData = new FormData();
    fileData.append('image', file)
    fileData.append('method', '1')
    fileData.append('description', '1')
    fileData.append('related_id', '1')
    fileData.append('user_id', userStore.userinfo.userId)
    uploadImg(fileData).then(result => {
      if(type === 'start') _data.image = result.data
      if(type === 'mask') _data.optImage = result.data
      resolve()
    }, err => {
      resolve()
    })
  })
};
const change = () => {
  // if(_data.sharpening>0) {
  //   canvas.draw(texture).brightnessContrast(calculationInterval(_data.brightness), calculationInterval(_data.contrast))
  //       .hueSaturation( 0 ,calculationInterval(_data.saturate))
  //       .unsharpMask(_data.sharpening, 0.6)
  //       .noise( calculationNoise(_data.noise))
  //       .update();
  // } else {
    canvas.draw(texture).brightnessContrast(calculationInterval(_data.brightness), calculationInterval(_data.contrast))
        .hueSaturation( 0 ,calculationInterval(_data.saturate))
        // .noise( calculationNoise(_data.noise))
        .update();
  // }
  _data.edtUrl = canvas.toDataURL('image/png');
}
const calculationInterval = (num) => {
   return (num -100) / 100
}
const calculationNoise = (num) => {
  return num / 200
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
    _data.url = r.result
    canvas = null
   if(texture) texture.destroy()
    init()
    // }
  };
  return false
}
const clearImage = () => {
  _data.url = ''
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
  .close-img{
    position: absolute;
    top: 20px;
    right: 0;
  }
  img {
    max-width: 100%;
    border-radius: 8px;
    max-height: 40vh;
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
      .ant-upload-file-tips{
        font-size: 12px;
      }
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
  .over {
    background: @bg-page-hover-color;
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
  //border-radius: 20px;
  //display: flex;
  //align-items: center;
  //justify-content: center;
  //color: #fff;
  //cursor: pointer;
  //background: linear-gradient(to right, #AC4FFE, #5A50FE 50%, #AC4FFE);
  //font-size: 16px;
  //.iconfont{
  //  font-size: 16px;
  //  margin-right: 5px;
  //}
  //&:hover {
  //  opacity: 0.8;
  //}
  .send-btn {
    width:100%;
    display: flex;
    font-size: 14px;
    cursor: pointer;
    color: #fff;
    border: 0;
    background: @btn-bg-color;
    .iconfont{
      fill: #FFFFFF;
      font-size: 14px;
      margin-right: 5px
    }
    &[disabled]{
      cursor: not-allowed!important;
    }
    &:hover {
      opacity: 0.8;
    }
  }
}

.slider-dot-customize {
  :deep(.ant-slider-rail) {
    background-color: #78797C;
  }

  :deep(.ant-slider-track) {
    background-color: #009BFE;
  }

  :deep(.ant-slider-dot) {
    background-color: #78797C;
    border-color: #78797C;
    height: 10px;
    width: 10px;
    margin-left: -5px;
    top: -3px;
    //&:nth-child(2) {
    //  height: 10px;
    //  width: 10px;
    //  margin-left: -5px;
    //  top: -3px;
    //}
    //
    //&:nth-child(3) {
    //  height: 12px;
    //  width: 12px;
    //  top: -4px;
    //  margin-left: -6px;
    //}
    //
    //&:nth-child(4) {
    //  height: 16px;
    //  width: 16px;
    //  top: -6px;
    //  margin-left: -8px;
    //}
    //
    //&:nth-child(5) {
    //  height: 20px;
    //  width: 20px;
    //  top: -8px;
    //  margin-left: -10px;
    //}
  }
  :deep(.ant-slider-dot-active){
    background-color: #009BFE;
    border-color: #009BFE;
  }
  :deep(.ant-slider-handle) {
    //background-color: #009BFE;
    border-color: #009BFE;
    height: 16px;
    width: 16px;
    margin-top: -6px;
  }
  :deep(.ant-slider-mark-text) {
    //background-color: #009BFE;
    font-size: 9px;
  }
}
</style>
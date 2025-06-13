<script setup>
// 图片裁剪
import {defineEmits, nextTick, ref, defineProps, reactive} from 'vue';
import './cropper/cropper.min.js';
import './cropper/cropper.min.css'
import {getUid} from "@/utils/utils.js";
const visible = ref(false);
const imageId = ref('image-id' + new Date().getTime() + getUid());
const _data = reactive({
  width: 0,
  height: 0
})
const props = defineProps({
  aspectRatio: {
    type:Number
  },
  outputWidth: {
    type:Number
  },
  outputHeight: {
    type:Number
  }
})
let cropper =  '';
const emit = defineEmits(['change']);
const handleOk = e => {
  //let options = { width:_data.width, height:_data.height }
  let options = {}
  if(props.outputWidth> 0){
    options = { width:props.outputWidth, height:props.outputHeight }
  }
  const canvas = cropper.getCroppedCanvas(options);
  const base64Image = canvas.toDataURL("image/png");
  emit('change', base64Image )
  visible.value = false;
  if(cropper){
    cropper.destroy();
  }
  cropper = ''
};
const showClip = url => {
  // src.value = url
  visible.value = true;
  imageId.value = 'image-id' + new Date().getTime() +  getUid()
  nextTick(() => {
    if(cropper){
      cropper.destroy();
    }
    // if(isHttp(url)){
    //   consoleurl
    //   convertImgToBase64(url,(base64)=>{
    //       console.log(base64)
    //   })
    // } else {
      init(url)
    // }
  })
};
const init = (url) => {
  const img = document.getElementById(imageId.value);
  img.src = url;
  img.onload = function () {
    _data.width = img.width
    _data.height = img.height
    let obj = {}
    if(props.aspectRatio>0){
      obj = {aspectRatio: props.aspectRatio }
    }
    cropper  = new Cropper(img, Object.assign({},obj,{
      aspectRatio: props.aspectRatio || null , // 裁剪框的宽高比
      viewMode: 1,
      dragMode: "move",
      autoCropArea: 0.8,
      cropBoxMovable: true,
      cropBoxResizable: true,
      background: true,
    }));
  };
};
defineExpose({
  showClip
})
</script>

<template>
  <a-modal :maskClosable="false" v-model:visible="visible" title="图片裁剪" :destroyOnClose="true" @ok="handleOk" width="80%">
    <div>
      <img :id="imageId" src="" alt=""/>
    </div>
  </a-modal>
</template>

<style scoped lang="less">
#image {
  max-width: 100%;
  max-height: 60vh;
}
</style>
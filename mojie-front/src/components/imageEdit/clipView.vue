<script setup>
// 图片裁剪
import {defineEmits, nextTick, defineProps, reactive, ref} from 'vue';
import './cropper/cropper.min.js';
import './cropper/cropper.min.css'
import {getUid} from "@/utils/utils.js";

const _data = reactive({
  width: 0,
  height: 0
})
const props = defineProps({
  aspectRatio: {
    type: Number
  },
  outputWidth: {
    type: Number
  },
  outputHeight: {
    type: Number
  }
})
let imageId = ref('image-id' + new Date().getTime() + getUid());
let cropper = '';
const emit = defineEmits(['change']);
const handleOk = e => {
  //let options = { width:_data.width, height:_data.height }
  let options = {}
  if (props.outputWidth > 0) {
    options = {width: props.outputWidth, height: props.outputHeight}
  }
  const canvas = cropper.getCroppedCanvas(options);
  const base64Image = canvas.toDataURL("image/png");
  emit('change', base64Image)

  if (cropper) {
    cropper.destroy();
  }
  cropper = ''
};
const showClip = url => {
  // src.value = url
  imageId.value = 'image-id' + new Date().getTime() + getUid()
  nextTick(() => {
    if (cropper) {
      cropper.destroy();
    }
    init(url)
  })
};
const init = (url) => {
  const img = document.getElementById(imageId.value);
  img.onload = function () {
    _data.width = img.width
    _data.height = img.height
    let obj = {}
    if (props.aspectRatio > 0) {
      obj = {aspectRatio: props.aspectRatio}
    }
    cropper = new Cropper(img, Object.assign({}, obj, {
      aspectRatio: props.aspectRatio || null, // 裁剪框的宽高比
      viewMode: 1,
      dragMode: "move",
      autoCropArea: 0.8,
      cropBoxMovable: true,
      cropBoxResizable: true,
      background: true,
    }));
  };
  img.src = url;
};
defineExpose({
  showClip,
  handleOk
})
</script>

<template>
  <div class="image-box flex justify-center items-center">
    <img :id="imageId" src="" alt=""/>
  </div>
</template>

<style scoped lang="less">
.image-box {
  width: 100%;
  height: calc(80vh - 148px);
  overflow: hidden;
  margin: 0 auto;
  img{
    max-height: 100%;
    max-width: 100%;
  }
}
</style>
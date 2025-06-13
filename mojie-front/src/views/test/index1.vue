<template>
  <div>
    <div class="flex">
      <div>
        <div>
          <a-upload accept="image/*"
                    :showUploadList="false"
                    list-type="picture"
                    :beforeUpload="previewFile">
            <a-button>
              上传图片
            </a-button>
          </a-upload>
        </div>
        <div v-if="imageUrl">
          <a-button @click="clip">
            裁剪
          </a-button>
        </div>
        <div v-if="imageUrl">
          <a-button @click="imageFabricShow('draw')">
            涂鸦
          </a-button>
        </div>
        <div v-if="imageUrl">
          <a-button @click="imageFabricShow('text')">
            文字
          </a-button>
        </div>
        <div v-if="imageUrl">
          <a-button @click="saveImage('text')">
            色彩
          </a-button>
        </div>
      </div>
      <div class="flex-1">
        <img :src="imageUrl"  alt="">
      </div>
      <div class="flex-1">
        <img :src="imageUrl" style="filter: brightness(200%) contrast(200%) saturate(200%);" alt="">
      </div>
      <div class="flex-1">
        <img :src="imageUrlChange" alt="">
      </div>
    </div>
    <ImageClip ref="ImageClipRef" @change="imageUrlClip"></ImageClip>
    <ImageFabric ref="ImageFabricRef" @change="imageUrlClip"></ImageFabric>
  </div>
</template>
<script setup>
import  ImageClip from '@/components/imageEdit/clip.vue'
import  ImageFabric from '@/components/imageEdit/fabric.vue'
import {reactive, ref} from "vue";
import {convertImgToBase64,compressFile} from "@/utils/utils.js";
const imageUrl = ref('')
const imageUrlChange = ref('')
const ImageClipRef = ref()
const ImageFabricRef = ref()
const _data = reactive({
  clipOpen: false
})
const previewFile =  file => {
  if (file.size > 3 * 1024 * 1024) {
    //message.error('上传的文件大小不能超过3M')
    compressFile(file,(newFile)=>{
      fileToBase64(newFile)
    })
  } else {

    fileToBase64(file)
  }
  return false
}
const fileToBase64 =  file => {
  let r = new FileReader();
  r.readAsDataURL(file);
  r.onload = () => { // 读取操作完成回调方法
    // that.$refs.canvas.upLoadImage(r.result);
    console.log(r.result)
    imageUrl.value = r.result
  };
  return false
}

const imageFabricShow =  (type) => {
  ImageFabricRef.value.showClip(imageUrl.value,type)
  //ImageClipRef.value.showClip('https://qihuaimage.tos-cn-guangzhou.volces.com/056fe605-8d97-42b4-9cb1-e76d3348c9d5.png')
}
const clip =  () => {
  ImageClipRef.value.showClip(imageUrl.value)
  //ImageClipRef.value.showClip('https://qihuaimage.tos-cn-guangzhou.volces.com/056fe605-8d97-42b4-9cb1-e76d3348c9d5.png')
}
const imageUrlClip =  (url) => {
  imageUrl.value = url
}
const saveImage = () => {
  convertImgToBase64(imageUrl.value,(base64)=>{
    imageUrlChange.value = base64
  },{
    brightness:200,
    contrast:200,
    saturate:200,
  })
}
</script>
<style scoped lang="less">
.flex{
  height: 100vh;
  width: 100vw;
  .flex-1{
    padding: 40px;
    margin: 0 auto;
    img{
      max-width: 100%;
      max-height: 60vh;
    }
  }
}
</style>
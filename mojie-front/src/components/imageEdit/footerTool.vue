<template>
  <div class="flex flex-1">
    <template v-if="drawType === 'draw'">
<!--      <div class="mr-10">-->
<!--        <label for="head"> 画笔颜色</label>-->
<!--        <input type="color" v-model="fontObj.color" @change="change" />-->
<!--      </div>-->
      <div class="mr-10 line-h-30">
        细
      </div>
      <div class="flex-1 text-left mr-10">
        <a-slider :min="10" :max="400" v-model:value="fontObj.width" @afterChange="change" />
      </div>
      <div class="line-h-30">
        粗
      </div>
    </template>
    <template v-if="drawType === 'text'">
      <div class="mr-10 line-h-30">
        <label for="head">文字颜色</label>
        <input type="color" v-model="fontObj.fill" @change="change"/>
      </div>
      <div class="mr-10 line-h-30">
        文字大小
      </div>
      <div class="flex-1 text-left mr-10">
        <a-slider :min="30" :max="200" v-model:value="fontObj.fontSize" @afterChange="change" />
      </div>
    </template>
  </div>
</template>
<script setup>
import {defineEmits, defineExpose, reactive} from "vue";
let drawType = 'draw'
const fontObj = reactive({
  width: 120,
  color: '#F80000',
  fontSize: 36,
  fill: '#F80000'
})
const emit = defineEmits(['change']);
// let time = null
const setFormValue = (obj,type) => {
  fontObj.width = obj.width
  fontObj.color = obj.color
  fontObj.fontSize = obj.fontSize
  fontObj.fill = obj.fill
  drawType = type
}
const change = () => {
  emit('change', fontObj)
  // if(time) clearTimeout(time)
  // time = setTimeout(()=>{
  //   emit('change', fontObj)
  // },50)
}
defineExpose({
  setFormValue
})
</script>
<style scoped lang="less">
.line-h-30{
  line-height: 30px;
}
</style>
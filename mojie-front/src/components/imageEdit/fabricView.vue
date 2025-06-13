<template>
  <div class="image-edt-box">
    <div class="image-view flex justify-center items-center" :class="drapClass" v-if="!imageUrl">
      <div class="up-btn flex items-center justify-center"  @click="uploadFile"  @drop.prevent="handleDrop"  @dragover.prevent="drapClassChange('over')"  @dragenter.prevent="drapClassChange('enter')" @dragleave="drapClassChange('leave')">
        <div class="text-center">
          <PlusOutlined :style="{fontSize: '26px'}"/>
          <div class="ant-upload-file-tips">添加图片(支持拖拽添加)</div>
        </div>
      </div>
    </div>
    <close-circle-filled class="close-img" v-if="imageUrl" @click="clearImage" />
    <div class="flex justify-center items-center canvas-content" :class="drapClass" ref="canvasBox" v-show="imageUrl" @drop.prevent="handleDrop"  @dragover.prevent="drapClassChange('over')"  @dragenter.prevent="drapClassChange('enter')" @dragleave="drapClassChange('leave')">
<!--      <div class="flex justify-center items-center" v-show="!drawType&&imageUrl">-->
<!--        <img class="image" :src="imageUrl" />-->
<!--      </div>-->
      <div class="flex justify-center items-center" v-show="drawType!=='clip'">
        <canvas :id="fabricId"/>
      </div>
      <clipView ref="ClipViewRef" v-bind="props" v-show="drawType==='clip'" @change="imageUrlClip"></clipView>
    </div>
    <div class="footer-btn mt-10">
      <div v-show="drawType==='draw'&&imageUrl" class="flex justify-center items-center">
        <div class="coarse-fine">
          <FooterTool ref="footerToolRef" @change="toolChange"></FooterTool>
        </div>
      </div>
      <div class="flex justify-center items-center">
        <div class="flex mt-10" v-show="drawType!=='clip'">
          <div class="image-btn flex mr-10">
            <div class="flex-1">
              <a-tooltip placement="bottom">
                <template #title>
                  <span>遮罩画笔</span>
                </template>
                  <i class="iconfont icon-huabi1" :class="{disabled:!imageUrl ||isTranslation }" @click="freeDraw"></i>
              </a-tooltip>
            </div>
            <div class="flex-1">
              <a-tooltip placement="bottom">
                <template #title>
                  <span>平移</span>
                </template>
                <i class="iconfont icon-pingyi" :class="{disabled:!imageUrl ||!isTranslation}" @click="tabTranslation"></i>
              </a-tooltip>
            </div>
            <div class="flex-1">
              <a-tooltip placement="bottom">
                <template #title>
                  <span>裁剪</span>
                </template>
                <i class="iconfont icon-caijian1" :class="{disabled:!imageUrl }" @click="clip"></i>
              </a-tooltip>
            </div>
            <div class="flex-1">
              <a-tooltip placement="bottom">
                <template #title>
                  <span>还原</span>
                </template>
                <i class="iconfont icon-zhongzhi3" :class="{disabled:!imageUrl }" @click="reset"></i>
              </a-tooltip>
            </div>
          </div>
          <div class="image-btn his flex">
            <div class="flex-1">
              <a-tooltip placement="bottom">
                <template #title>
                  <span>上一步</span>
                </template>
                <i class="iconfont icon-weibiaoti545" :class="{disabled:operateListIndex === 0 }" title="上一步" @click="prevDraw"></i>
              </a-tooltip>
            </div>
            <div class="flex-1">
              <a-tooltip placement="bottom">
                <template #title>
                  <span>下一步</span>
                </template>
                <i class="iconfont icon-weibiaoti546" :class="{disabled:operateListIndex >= operateList.length - 1 }"   title="下一步" @click="nextDraw"></i>
              </a-tooltip>
            </div>
          </div>
        </div>
        <div v-show="drawType==='clip'">
          <div class="image-btn clip flex">
            <div class="flex-1 "  @click="cancelClip">
              取消
            </div>
            <div class="flex-1" @click="handleClip">
              完成裁剪
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import FooterTool from "@/components/imageEdit/footerTool.vue";
import clipView from "@/components/imageEdit/clipView.vue";

import {CloseCircleFilled, PlusOutlined} from '@ant-design/icons-vue';
import {defineEmits, nextTick, reactive, defineExpose, ref, defineProps} from 'vue';
import {fabric} from "fabric";
import {base64UrlToFile, compressFile, convertImgToBase64, getUid, isHttp, isImageFile} from "@/utils/utils.js";
import {message} from "ant-design-vue";
import emitter from "@/utils/emitter.js";
import {httpIndex} from "@/options/model.js";
const footerToolRef = ref();
const canvasBox = ref();
const ClipViewRef = ref();
const drawType = ref('draw');
const imageUrl = ref('');
const saveUrl = ref('');
const zoomInfo = ref({});
const isTranslation = ref(false);
let canvas = null;
let zoom = 1;
let canvasInfo = {}
let bottomImage = null
const fabricId = ref('fabric-canvas' + new Date().getTime() + getUid());
const props = defineProps({
  type: {
    type: String,
    default: ''
  }
})
const emit = defineEmits(['change']);
const fontObj = reactive({
  width: 120
})

//操作记录
let operateList = ref([])
let operateListIndex = ref(0)
const removeImageCanvas = () => {
  for (let item of canvas.getObjects()) {
    if(item.type === 'image') {
      canvas.remove(item);
    }
  }
}
const handleOk = (type) => {
  // drawType.value = 'clip'
  if(drawType.value==='clip'){
    message.error('请先完成裁剪或取消裁剪')
    return
  }
  if(canvas.getZoom()!== zoom){
    // message.error('请将图片编辑区缩放还原，在进行操作')
    canvas.zoomToPoint({x: zoomInfo.value.offsetX, y:zoomInfo.value.offsetY}, zoom); // 以鼠标指针来缩放画板
    canvas.viewportTransform[4] = 0
    canvas.viewportTransform[5] = 0
    canvas.requestRenderAll(); // 异步更新画板，提升性能
    //message.error('请将缩放至最小缩放')
    ///return
  }
  if (canvas) {
    canvas.setWidth(canvasInfo.width);
    canvas.setHeight(canvasInfo.height);
    canvas.setZoom(1);
    const base64Image = canvas.toDataURL("image/png");
    let mask_image = ''
    if (type === 'mask') {
      canvas.remove(bottomImage)
      removeImageCanvas()
      mask_image = canvas.toDataURL("image/png");
      canvas.add(bottomImage)
      bottomImage.selectable = false;
      bottomImage.movable = false;
      canvas.sendToBack(bottomImage);
    }
    canvas.setWidth(canvasInfo.canvasWidth);
    canvas.setHeight(canvasInfo.canvasHeight);
    canvas.setZoom(zoom);
    const flag = hasFreeDraw()
    emit('change',saveUrl.value, base64Image,mask_image,flag)
    //canvasClear()
  }
};
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
const hasFreeDraw = (arr) => {
  let flag = false;
  for (let item of canvas.getObjects()) {
    if(item.type === 'path') {
      flag = true
      break;
    }
  }
  return flag
}
const canvasClear = () => {
  if(canvas){
    canvas.clear(); // 这个方法实际上是移除所有对象并清除背景的快捷方式
    canvas.dispose();
// 删除画布元素（可选）
    canvas = null;
  }
  emitter.off(props.type +  '-move', windowMousemove);
  emitter.off(props.type +  '-up', windowMouseup);
};
const toolChange = (obj) => {
  fontObj.width = obj.width
  canvas.freeDrawingBrush.width = obj.width;
}
const clearHistoryList = () => {
  operateList.value = []
  operateListIndex.value = 0
  canvasClear()
}

const init = async (url) => {
  if(canvas){
    canvas.clear();
    canvas.dispose();
    // 删除画布元素（可选）
    canvas = null;
  }
  emitter.on(props.type +  '-move', windowMousemove);
  emitter.on(props.type +  '-up', windowMouseup);
  const imageInfo = await initCanvasSize(url)
  canvasInfo = {
    width: imageInfo.imaged.width,
    height: imageInfo.imaged.height,
    canvasWidth: imageInfo.width,
    canvasHeight: imageInfo.height,
  }
  await initCas();
  await imageAddCanvas(imageInfo)
  // 注册画布事件
  initEvent();
  operateList.value.push({canvas: JSON.stringify(canvas),canvasInfo:{
      ...canvasInfo,
      zoom:zoom,
      saveUrl:url
  }});// 将操作存在记录里
  operateListIndex.value = operateList.value.length - 1;
  freeDraw()
};
// 初始化画布尺寸
const initCanvasSize = (url) => {
  var canvasEle = document.getElementById(fabricId.value)
  return new Promise(function (resolve) {
    var imaged = new Image()
    imaged.crossOrigin = 'Anonymous'
    imaged.src = url
    imaged.onload = function () {
      let width = imaged.width
      let height = imaged.height
      let r = height / width
      let maxWidth = canvasBox.value.offsetWidth
      let maxHeight = canvasBox.value.offsetHeight
      let cHeight = maxWidth * r
      if (cHeight > maxHeight) {
        let rh = width / height
        canvasEle.width = maxHeight * rh
        canvasEle.height = maxHeight
        zoom = maxHeight / height
        resolve({imaged, width: maxHeight * rh, height: maxHeight})
      } else {
        canvasEle.width = maxWidth
        canvasEle.height = cHeight
        zoom = cHeight / height
        resolve({imaged, width: maxWidth, height: cHeight})
      }
    }
  })
}
const imageAddCanvas = (imageInfo) => {
  return new Promise(function (resolve) {
    let left = 0
    let top = 0
    bottomImage = new fabric.Image(imageInfo.imaged, {
      cornerStyle: 'circle',
      cornerStrokeColor: 'blue',
      cornerColor: 'blue',
      cornerSize: 13,
      left,
      top
    })
    canvas.add(bottomImage)
    bottomImage.selectable = false;
    bottomImage.movable = false;
    resolve(canvas)
  })
}
const initCas = () => {
  return new Promise(function (resolve) {
    canvas = new fabric.Canvas(fabricId.value, {
      backgroundColor: '#000000',
    });
    // 初始化画布状态
    canvas.hasDraw = false;
    // canvas.setZoom(zoom);
    canvas.zoom = zoom;
    canvas.setWidth(canvasInfo.canvasWidth);
    canvas.setHeight(canvasInfo.canvasHeight);
    canvas.setZoom(zoom);
    resolve(canvas)
  })
};
const initEvent = () => {
  canvas.on("mouse:down", onMouseDown);
  canvas.on("mouse:move", onMouseMove);
  canvas.on("mouse:up", onMouseUp);
  canvas.on("mouse:wheel", onMouseWheel);
  canvas.on("mouse:out", onMouseOut);
};
//画笔
const freeDraw = (e) => {
  isTranslation.value =false
  if(!imageUrl.value) return;
  canvas.isDrawingMode = true
  canvas.freeDrawingBrush.color = '#ffffff';
  // canvas.freeDrawingBrush.color = 'rgba(255, 255, 255, 0.6)';
  canvas.freeDrawingBrush.width = fontObj.width;
  drawType.value = 'draw'
  // canvas.style.cursor = 'url("path/to/round-cursor.png"), auto';
  // if (fabric.PatternBrush) {
  //   //设置黑白格画笔
  //   const squarePatternBrush = new fabric.PatternBrush(canvas);
  //   squarePatternBrush.getPatternSrc = function () {
  //
  //     const squareWidth = 10, squareDistance = 10;
  //
  //     const patternCanvas = fabric.document.createElement('canvas');
  //     patternCanvas.width = patternCanvas.height = squareWidth + squareDistance;
  //     const ctx = patternCanvas.getContext('2d');
  //
  //     ctx.fillStyle = '#ffffff';
  //     ctx.fillRect(0, 0, squareWidth, squareWidth);
  //     ctx.fillStyle = '#000000';
  //     ctx.fillRect(0, 10, squareWidth, squareWidth);
  //     ctx.fillStyle = '#000000';
  //     ctx.fillRect(10, 0, squareWidth, squareWidth);
  //     ctx.fillStyle = '#ffffff';
  //     ctx.fillRect(10, 10, squareWidth, squareWidth);
  //     return patternCanvas;
  //   };
  //   canvas.freeDrawingBrush = squarePatternBrush;
  //
  //   canvas.freeDrawingBrush.width = fontObj.width;
  //   if (canvas.freeDrawingBrush) {
  //     const brush = canvas.freeDrawingBrush;
  //     brush.color = '#000000';
  //     if (brush.getPatternSrc) {
  //       brush.source = brush.getPatternSrc.call(brush);
  //     }
  //     brush.width = parseInt(fontObj.width, 10) || 1;
  //     brush.shadow = new fabric.Shadow({
  //       blur: parseInt(30, 10) || 0,
  //       offsetX: 0,
  //       offsetY: 0,
  //       affectStroke: true,
  //       color: "#ffffff",
  //     });
  //     brush.selectable = false;
  //     brush.movable = false;
  //   }
  // }
};
const tabTranslation = () => {
  if(zoom===canvas.getZoom()){
    message.info('请先滚轮放大后再平移')
     return
  }
  canvas.isDrawingMode = false;
  isTranslation.value = true
  canvas.selection = false; // 禁用选择框，使拖动更加直观
  canvas.forEachObject(function(o) { o.selectable = false; });
};
const moveInfo = ref({
  startX:0,
  startY:0,
  isDown: false
})
const onMouseDown = options => {
  if(!isTranslation.value||canvas.getZoom()=== zoom) return
  moveInfo.value.startX = options.e.clientX;
  moveInfo.value.startY = options.e.clientY;
  moveInfo.value.isDown = true
};
const onMouseMove = options => {
  if(canvas.isDrawingMode&&drawType.value==='draw') {
    const cursor = document.getElementById('fabric-'+ props.type+'-cursor')
    cursor.style.display = `block`
    const cWidth = canvas.width * canvas.getZoom() / zoom
    const _width = fontObj.width * (cWidth/canvasInfo.width)
    cursor.style.width = `${_width}px`
    cursor.style.height = `${_width}px`
    cursor.style.left = `${options.e.clientX -_width/2}px`
    cursor.style.top = `${options.e.clientY - _width/2}px`
  }
  if(canvas.getZoom()=== zoom) return
  if (options.e.button === 0 &&isTranslation.value&&moveInfo.value.isDown) { // 确保是左键拖动
    const moveX = options.e.clientX - moveInfo.value.startX;
    const moveY = options.e.clientY - moveInfo.value.startY;
    moveInfo.value.startX = options.e.clientX; // 更新起始点坐标以实现连续拖动效果
    moveInfo.value.startY = options.e.clientY;
    canvas.viewportTransform[4] += moveX;
    canvas.viewportTransform[5] += moveY;
    limitOutOfRange()
  }
};
const onMouseOut = options => {
  const cursor = document.getElementById('fabric-'+ props.type+'-cursor')
  cursor.style.display = `none`
};
const onMouseWheel = opt => {
  const delta = opt.e.deltaY; // 正值为放大
  let _zoom = canvas.getZoom();
  if(_zoom === zoom) zoomInfo.value = opt.e
  _zoom *= 0.999 ** delta;
  if (_zoom > 20) _zoom = 20
  if (_zoom < zoom) _zoom = zoom;
  canvas.zoomToPoint({x: zoomInfo.value.offsetX, y:zoomInfo.value.offsetY}, _zoom); // 以鼠标指针来缩放画板
  if(canvas.isDrawingMode&&drawType.value==='draw') {
    canvas.freeDrawingBrush.width = fontObj.width;

    const cursor = document.getElementById('fabric-'+ props.type+'-cursor')
    const cWidth = canvas.width * canvas.getZoom() / zoom
    const _width = fontObj.width * (cWidth/canvasInfo.width)
    cursor.style.width = `${_width /2}px`
    cursor.style.height = `${_width/2}px`
  }

  if(_zoom === zoom) {
    canvas.viewportTransform[4] = 0
    canvas.viewportTransform[5] = 0
    moveInfo.value.isDown = false
    canvas.isDrawingMode = true;
    drawType.value = 'draw'
    isTranslation.value = false
  }
  limitOutOfRange()
};
//限制超出图片区域
const limitOutOfRange = () => {
  if (canvas.viewportTransform[4] > 0) canvas.viewportTransform[4] = 0
  if (canvas.viewportTransform[5] > 0) canvas.viewportTransform[5] = 0
  const cWidth = canvas.width * canvas.getZoom() / zoom
  const cHeight = canvas.height * canvas.getZoom() / zoom
  if (canvas.viewportTransform[5] < (canvas.height - cHeight)) canvas.viewportTransform[5] = (canvas.height - cHeight)
  if (canvas.viewportTransform[4] < (canvas.width - cWidth)) canvas.viewportTransform[4] = (canvas.width - cWidth)
  canvas.requestRenderAll(); // 异步更新画板，提升性能
}
const onMouseUp = opt => {
  moveInfo.value.isDown = false
  if(canvas.getZoom()!== zoom) return
  if (opt.target&&drawType.value ==='draw') {
    if (operateListIndex.value < operateList.value.length - 1) {
      operateList.value.splice(operateListIndex.value + 1);
    }
    operateList.value.push({canvas: JSON.stringify(canvas),canvasInfo:{
        ...canvasInfo,
        zoom:zoom,
        saveUrl:saveUrl.value
      }});// 将操作存在记录里
    operateListIndex.value = operateList.value.length - 1;
  }
};
const imageUrlClip = (url) => {
   drawType.value = 'draw'
   saveUrl.value = url
   init(url)
}
const clip = () => {
  drawType.value = 'clip'
  nextTick(() => {
    // if (canvas) {
    //   // drawType.value = 'clip'
    //   // canvas.setWidth(canvasInfo.width);
    //   // canvas.setHeight(canvasInfo.height);
    //   // canvas.setZoom(1);
    //   // const base64Image = canvas.toDataURL("image/png");
    //   // canvas.setWidth(canvasInfo.canvasWidth);
    //   // canvas.setHeight(canvasInfo.canvasHeight);
    //   // canvas.setZoom(zoom);
    //   ClipViewRef.value.showClip(saveUrl.value)
    // }
    if(saveUrl.value) ClipViewRef.value.showClip(saveUrl.value)
  })
};
const reset = () => {
  if(canvas&&imageUrl.value){
    //drawType.value = 'draw'
    clearHistoryList()
    init(imageUrl.value)
  }
};
const resetToParent = () => {
  if(canvas){
    emit('change', imageUrl.value)
  }
};
const setInit = (url) => {
  if(url){
    convertImgToBase64(url,(base64)=>{
      clearImage()
      const draFile = base64UrlToFile(base64)
      previewFile(draFile)
    })
  }
};
const handleClip = () => {
  ClipViewRef.value.handleOk()
};
const cancelClip = () => {
  if (canvas) {
    canvas.setWidth(canvasInfo.canvasWidth);
    canvas.setHeight(canvasInfo.canvasHeight);
    canvas.setZoom(zoom);
    limitOutOfRange()
  }
  drawType.value = 'draw'
};
const prevDraw = () => {
  if (operateListIndex.value > 0) {
    let index = operateListIndex.value - 1;
    operateListIndex.value = index;
    canvas.loadFromJSON(operateList.value[index].canvas);
    lockObj(canvas,operateList.value[index].canvasInfo,'his')
  }
};
const nextDraw = () => {
  if (operateListIndex.value < operateList.value.length - 1) {
    let index = operateListIndex.value + 1;
    operateListIndex.value = index;
    canvas.loadFromJSON(operateList.value[index].canvas);
    lockObj(canvas,operateList.value[index].canvasInfo,'his')
  }
};
const windowMousemove = e => {
  hideCursor(e)
};
const windowMouseup = e => {
  hideCursor(e)
};
const hideCursor = e => {
  const canvasEle = document.getElementById(fabricId.value)
  if(canvasEle&&canvasEle.getBoundingClientRect()){
    const rect = canvasEle.getBoundingClientRect();
    const mouseX = e.clientX; // 可能需要从事件或其他地方获取这个值，例如通过参数传递或使用全局状态管理库如Vuex来存储鼠标位置。
    const mouseY = e.clientY; // 同上。
    if (mouseX < rect.left || mouseX > rect.right || mouseY < rect.top || mouseY > rect.bottom) {
      const cursor = document.getElementById('fabric-'+ props.type+'-cursor')
      cursor.style.display = `none`
    }
  }
};
const lockObj = (arr,info,type) =>{
  // arr canvas对象
  canvasInfo = info
  zoom = info.zoom
  saveUrl.value = info.saveUrl
  setTimeout(function () {
    canvas.setWidth(canvasInfo.canvasWidth);
    canvas.setHeight(canvasInfo.canvasHeight);
    canvas.setZoom(canvasInfo.zoom);
    arr.getObjects().forEach(function (item) {
      item.lockMovementX = true; // 禁止水平移动
      item.lockMovementY = true; // 禁止垂直移动
      item.hasRotatingPoint = false; // 无旋转点
      item.hasControls = false; // 编辑框
      item.selectable = false; // 不可选中
      item.movable = false;
      if(item.type==='image') {
        bottomImage = item
      }
    });
    if(type==='his'){
      canvas.zoomToPoint({x: 0, y: 0}, zoom); // 以鼠标指针来缩放画板
      canvas.viewportTransform[4] = 0
      canvas.viewportTransform[5] = 0
      canvas.requestRenderAll(); // 异步更新画板，提升性能
    }
  }, 200);
}
const previewFile = file => {
  fabricId.value = 'fabric-canvas' + new Date().getTime()  +  getUid()
  drawType.value = 'draw'
  if (file.size > 3 * 1024 * 1024) {
    compressFile(file, (newFile) => {
      fileToBase64(newFile)
    })
  } else {
    fileToBase64(file)
  }
  return false
}
const uploadFile = file => {
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
    imageUrl.value = r.result
    saveUrl.value = r.result
    init(imageUrl.value)
  };
  return false
}
const clearImage = () => {
  imageUrl.value = ''
  saveUrl.value = ''
  drawType.value = ''
  clearHistoryList()
}
defineExpose({
  clearHistoryList,
  resetToParent,
  setInit,
  handleOk
})
</script>
<style scoped lang="less">
.image-edt-box{
  position: relative;
  .image-view {
    width: 100%;
    height: 220px;
    background: @bg-page-color;
    border-radius: 8px;
    .up-btn {
      padding: 10px 5px;
      width: 100%;
      height: 200px;
      cursor: pointer;
      .ant-upload-file-tips{
        font-size: 12px;
      }
    }
    &:hover{
      background: @bg-page-hover-color;
    }
  }
  .over{
    background: @bg-page-hover-color!important;
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
  .canvas-content {
    width: 100%;
    height: 400px;
    overflow: hidden;
    background-color: @bg-page-color;
    >div{
      height: 100%;
      width: 100%;
    }
    .image{
      max-width: 100%;
      max-height: 100%;
    }
  }

  .coarse-fine {
    width: 320px;
    padding: 0 20px;
    background-color: #2F2F2F;
    border-radius: 20px;
  }

  .footer-btn {
    .image-btn {
      width: 150px;
      padding: 6px;
      height: 32px;
      font-size: 12px;
      text-align: center;
      color: #FFFFFF;
      border-radius: 20px;
      background-color: #303030;

      &.his {
        width: 100px;
      }
      > .flex-1 {
        line-height: 20px;

        .iconfont {
          font-size: 16px;
          cursor: pointer;
          &.disabled{
            color: #5e5959;
          }
        }
      }
      &.clip{
        color: #FFFFFF;
        > .flex-1 {
          cursor: pointer;
        }
      }
    }
  }
}
</style>
<template>
  <a-modal class="image-edt-modal"  wrapClassName="wrap-edt-image" :after-close="afterClose" :maskClosable="false" v-model:visible="visible" :destroyOnClose="true" @ok="handleOk"
           width="80%">
    <template #title>
      <div class="flex">
        <div class="title">{{ modalInfo[props.type][drawType] }}</div>
        <div class="flex-1 tips">
          * {{ modalInfo[props.type].tips }}
        </div>
      </div>
    </template>
    <!--    <a-spin :spinning="loading">-->
    <div class="flex justify-center items-center canvas-content" ref="canvasBox" v-show="drawType==='draw'">
      <canvas :id="fabricId"/>
    </div>
    <clipView ref="ClipViewRef" v-bind="props" v-show="drawType==='clip'" @change="imageUrlClip"></clipView>
    <!--    </a-spin>-->
    <template #footer>
      <div class="flex footer-btn">
        <div class="coarse-fine mr-10" v-show="drawType!=='clip'">
          <FooterTool ref="footerToolRef" @change="toolChange"></FooterTool>
        </div>
        <div class="image-btn flex mr-10" v-show="drawType!=='clip'">
          <div class="flex-1">
            <a-tooltip placement="bottom">
              <template #title>
                <span>遮罩画笔</span>
              </template>
              <i class="iconfont icon-huabi1" :class="{disabled:isTranslation }" @click="tabDraw"></i>
            </a-tooltip>
          </div>
          <div class="flex-1">
            <a-tooltip placement="bottom">
              <template #title>
                <span>平移</span>
              </template>
              <i class="iconfont icon-pingyi" :class="{disabled:!isTranslation }" @click="tabTranslation"></i>
            </a-tooltip>
          </div>
          <div class="flex-1">
            <a-tooltip placement="bottom">
              <template #title>
                <span>裁剪</span>
              </template>
              <i class="iconfont icon-caijian1" @click="clip"></i>
            </a-tooltip>
          </div>
          <div class="flex-1">
            <a-tooltip placement="bottom">
              <template #title>
                <span>还原</span>
              </template>
              <i class="iconfont icon-zhongzhi3" @click="reset"></i>
            </a-tooltip>
          </div>
        </div>
        <div class="image-btn his flex mr-10" v-show="drawType!=='clip'">
          <div class="flex-1">
            <a-tooltip placement="bottom">
              <template #title>
                <span>上一步</span>
              </template>
              <i class="iconfont icon-weibiaoti545" :class="{disabled:operateListIndex === 0 }" @click="prevDraw"></i>
            </a-tooltip>
          </div>
          <div class="flex-1">
            <a-tooltip placement="bottom">
              <template #title>
                <span>下一步</span>
              </template>
              <i class="iconfont icon-weibiaoti546" :class="{disabled:operateListIndex >= operateList.length - 1 }"
                 @click="nextDraw"></i><br>
            </a-tooltip>
          </div>
        </div>
        <div class="flex-1"></div>
        <div>
          <!--          <a-button type="primary" @click="handleOk"  v-show="drawType==='draw'">-->
          <a-button type="primary" @click="cancelClip" v-show="drawType==='clip'">
            取消
          </a-button>
          <a-button type="primary" @click="handleClip" v-show="drawType==='clip'">
            <template #icon>
              <check-outlined/>
            </template>
            完成裁剪
          </a-button>
          <a-button type="primary" @click="handleOk" v-show="drawType==='draw'" :loading="loading">
            <template #icon>
              <check-outlined/>
            </template>
            保存
          </a-button>
        </div>
      </div>
    </template>
  </a-modal>
</template>
<script setup>
import FooterTool from "@/components/imageEdit/footerTool.vue";
import clipView from "@/components/imageEdit/clipView.vue";

import {CheckOutlined} from '@ant-design/icons-vue';
import {defineEmits, nextTick, reactive, defineExpose, ref, defineProps, onMounted, onUnmounted} from 'vue';
import {fabric} from "fabric";
import {getUid} from "@/utils/utils.js";
import {message} from "ant-design-vue";
import emitter from "@/utils/emitter.js";

const modalInfo = {
  pro: {
    draw: '产品图涂抹',
    clip: '产品图裁剪',
    tips: '对产品以外的区域进行裁剪涂抹，能有效的提高迁移替换效果'
  },
  replace: {
    draw: '场景图涂抹',
    clip: '场景图裁剪',
    tips: '对场景图需要替换的区域进行涂抹，能有效的提高迁移替换效果'
  }
}
const visible = ref(false);
const loading = ref(false);
const footerToolRef = ref();
const canvasBox = ref();
const ClipViewRef = ref();
const drawType = ref('draw');
const clipType = ref('');
const resetUrl = ref('');
const clipUrl = ref('');
const initUrl = ref('');
const lastCanvas = ref('');
const isTranslation = ref(false);
const zoomInfo = ref({
  offsetX: 0, offsetY: 0
});
let bottomImage = null
let canvas = null;
let zoom = 1;
const fabricId = ref('fabric-canvas' + new Date().getTime() + getUid());
let canvasInfo = {}
const props = defineProps({
  type: {
    type: String,
    default: ''
  },
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
const emit = defineEmits(['change']);
const fontObj = reactive({
  width: 120
})

//操作记录
const operateList = ref([])
const operateListIndex = ref(0)
const handleOk = e => {
  if (drawType.value === 'clip') {
    message.error('请先完成裁剪或取消裁剪')
    return
  }
  if (canvas.getZoom() !== zoom) {
    canvas.zoomToPoint({x: zoomInfo.value.offsetX, y: zoomInfo.value.offsetY}, zoom); // 以鼠标指针来缩放画板

    canvas.viewportTransform[4] = 0
    canvas.viewportTransform[5] = 0
    canvas.requestRenderAll(); // 异步更新画板，提升性能
    // message.error('请将图片编辑区缩放还原，在进行操作')
    // return
  }
  if (canvas) {
    loading.value = true
    // const aaaBase = getWidthMask()
    canvas.setWidth(canvasInfo.width);
    canvas.setHeight(canvasInfo.height);
    canvas.setZoom(1);
    const base64Image = canvas.toDataURL("image/png");
    let mask_image = ''
    if (props.type === 'replace') {
      canvas.remove(bottomImage)
      removeImageCanvas()
      mask_image = canvas.toDataURL("image/png");
      // canvas.add(bottomImage);
      // bottomImage.selectable = false;
      // canvas.sendToBack(bottomImage);
    }
    canvas.setWidth(canvasInfo.canvasWidth);
    canvas.setHeight(canvasInfo.canvasHeight);
    canvas.setZoom(zoom);
    lastCanvas.value = {
      canvasInfo: canvasInfo,
      zoom: zoom,
      canvas: JSON.stringify(canvas),
      initUrl: initUrl.value
    }
    const flag = hasFreeDraw()
    emit('change', base64Image, initUrl.value, mask_image, flag)
    afterClose()
    visible.value = false;
    loading.value = false
    //  canvasClear()
  }
};
//生成黑底白涂遮罩
const getWidthMask = e => {
  const maskCanvasEl = document.createElement('canvas')
  maskCanvasEl.width = canvasInfo.width
  maskCanvasEl.height = canvasInfo.height
  const maskCanvas = new fabric.Canvas(maskCanvasEl, {backgroundColor: '#ffffff'});
  // 初始化画布状态
  maskCanvas.hasDraw = false;
  maskCanvas.setZoom(zoom);
  maskCanvas.zoom = zoom;
  //添加涂鸦
  for (let item of canvas.getObjects()) {
    if (item.type === 'path') {
      let clonedObject = fabric.util.object.clone(item);
      clonedObject.stroke='#000000'
      maskCanvas.add(clonedObject)
    }
  }
  maskCanvas.setWidth(canvasInfo.width);
  maskCanvas.setHeight(canvasInfo.height);
  maskCanvas.setZoom(1);
  const maskBase64 = maskCanvas.toDataURL("image/png");
  //emit('mask-change',maskBase64)
  maskCanvas.clear();
  maskCanvas.dispose();
  canvas.renderAll(); // 渲染更新后的 canvas
  return maskBase64
};
const afterClose = e => {
  emitter.off('fabric-modal-up')
  emitter.off('fabric-modal-move')
};
const windowMousemove = e => {
  hideCursor(e)
};
const windowMouseup = e => {
  hideCursor(e)
};
const hideCursor = e => {
  const canvasEle = document.getElementById(fabricId.value)
  if(!canvasEle) return
  const rect = canvasEle.getBoundingClientRect();
  const mouseX = e.clientX; // 可能需要从事件或其他地方获取这个值，例如通过参数传递或使用全局状态管理库如Vuex来存储鼠标位置。
  const mouseY = e.clientY; // 同上。
  if (mouseX < rect.left || mouseX > rect.right || mouseY < rect.top || mouseY > rect.bottom) {
    const cursor = document.getElementById('fabric-modal-cursor')
    cursor.style.display = `none`
  }
};

const cancel = e => {
  visible.value = false;
  loading.value = false
  afterClose()
};
const canvasClear = (type) => {
// 删除画布元素（可选）
  if (canvas) {
    canvas.clear();
    canvas.dispose();
    // 删除画布元素（可选）
    canvas = null;
  }
  if (type === 'init') return
  clipType.value = '';
  clipUrl.value = '';
  initUrl.value = '';
  lastCanvas.value = '';
  bottomImage = null
  zoom = 1;
  canvasInfo = {}
};
const showClip = (url, str, cType) => {
  emitter.on('fabric-modal-up', windowMouseup);
  emitter.on('fabric-modal-move', windowMousemove);
  fabricId.value = 'fabric-canvas' + new Date().getTime() + getUid()
  visible.value = true;
  loading.value = false
  drawType.value = str;
  clipType.value = cType || '';
  resetUrl.value = url
  if (!str) return
  nextTick(() => {
    if (str === 'clip') {
      clipUrl.value = url
      ClipViewRef.value.showClip(url)
    } else {
      footerToolRef.value.setFormValue(fontObj, 'draw')
      if (lastCanvas.value && lastCanvas.value.canvasInfo) {
        edtInit(url)
        return
      }
      init(url)
    }
  })
};
const toolChange = (obj) => {
  fontObj.width = obj.width
  if (drawType.value === 'draw') {
    canvas.freeDrawingBrush.width = obj.width;
  }
}
const clearHistoryList = () => {
  operateList.value = []
  clipType.value = ''
  canvasClear()
}

const edtInit = async (url) => {

  initUrl.value = url
  const imageInfo = await initCanvasSize(url)
  canvasInfo = {
    width: imageInfo.imaged.width,
    height: imageInfo.imaged.height,
    canvasWidth: imageInfo.width,
    canvasHeight: imageInfo.height,
  }
  await initCas();
  canvas.loadFromJSON(lastCanvas.value.canvas);
  lockObj(canvas)
  removeImageCanvas()
  await imageAddCanvas(imageInfo, 'edt')
  // 注册画布事件
  initEvent();
  freeDraw()
};
const init = async (url) => {
  if (canvas) {
    canvasClear('init')
  }
  initUrl.value = url
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
  operateList.value.push({
    canvas: JSON.stringify(canvas), canvasInfo: {
      ...canvasInfo,
      zoom: zoom,
      initUrl: initUrl.value
    }
  });// 将操作存在记录里
  // operateList.value.push(JSON.stringify(canvas));// 将操作存在记录里
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
      let maxWidth = document.body.offsetWidth * 0.8 - 48
      let maxHeight = document.body.offsetHeight * 0.8 - 192
      let cHeight = maxWidth * r
      if (cHeight > maxHeight) {
        let rh = width / height
        canvasEle.width = maxHeight * rh
        canvasEle.height = maxHeight
        canvasBox.value.style.height = maxHeight + 'px'
        zoom = maxHeight / height
        resolve({imaged, width: maxHeight * rh, height: maxHeight})
      } else {
        canvasEle.width = maxWidth
        canvasEle.height = cHeight
        canvasBox.value.style.height = cHeight + 'px'
        zoom = cHeight / height
        resolve({imaged, width: maxWidth, height: cHeight})
      }
    }
  })
}
const imageAddCanvas = (imageInfo, type) => {
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
    canvas.sendToBack(bottomImage);
    resolve(canvas)
  })
}
const initCas = () => {
  return new Promise(function (resolve) {
    canvas = new fabric.Canvas(fabricId.value, {backgroundColor: '#000000'});
    // 初始化画布状态
    canvas.hasDraw = false;
    canvas.setZoom(zoom);
    canvas.zoom = zoom;
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
  canvas.freeDrawingBrush.color = '#ffffff';
  canvas.freeDrawingBrush.width = fontObj.width;
  canvas.isDrawingMode = true;
  drawType.value = 'draw';
  // console.log(canvas);
  // canvas.style.cursor = 'url("'+cursorPng+'"), auto';
  // if(fabric.PatternBrush) {
  //   //设置黑白格画笔
  //   const squarePatternBrush = new fabric.PatternBrush(canvas);
  //   squarePatternBrush.getPatternSrc = function() {
  //
  //     const squareWidth = 10, squareDistance = 10;
  //
  //     const patternCanvas = fabric.document.createElement('canvas');
  //     patternCanvas.width = patternCanvas.height = squareWidth + squareDistance;
  //     const ctx = patternCanvas.getContext('2d');
  //
  //     ctx.fillStyle = 'rgba(255,255,255,0.3)';
  //     ctx.fillRect(0, 0, squareWidth, squareWidth);
  //     ctx.fillStyle =  'rgba(0,0,0,0.3)';
  //     ctx.fillRect(0, 10, squareWidth, squareWidth);
  //     ctx.fillStyle =  'rgba(0,0,0,0.3)';
  //     ctx.fillRect(10, 0, squareWidth, squareWidth);
  //     ctx.fillStyle =  'rgba(255,255,255,0.3)';
  //     ctx.fillRect(10, 10, squareWidth, squareWidth);
  //     return patternCanvas;
  //   };
  //   canvas.freeDrawingBrush = squarePatternBrush;
  //
  //   canvas.freeDrawingBrush.width = fontObj.width;
  //   if (canvas.freeDrawingBrush) {
  //     const brush = canvas.freeDrawingBrush;
  //     brush.color = 'rgba(0,0,0,0.3)';
  //     if (brush.getPatternSrc) {
  //       brush.source = brush.getPatternSrc.call(brush);
  //     }
  //     brush.width = parseInt( fontObj.width, 10) || 1;
  //     // brush.shadow = new fabric.Shadow({
  //     //   blur: parseInt(30, 10) || 0,
  //     //   offsetX: 0,
  //     //   offsetY: 0,
  //     //   affectStroke: true,
  //     //   color: "#ffffff",
  //     // });
  //   }
  // }
};
const moveInfo = ref({
  startX: 0,
  startY: 0,
  isDown: false
})
const onMouseDown = options => {
  if (!isTranslation.value || canvas.getZoom() === zoom) return
  moveInfo.value.startX = options.e.clientX;
  moveInfo.value.startY = options.e.clientY;
  moveInfo.value.isDown = true
};
const onMouseMove = options => {

  if(canvas.isDrawingMode&&drawType.value==='draw') {
    const cursor = document.getElementById('fabric-modal-cursor')
    cursor.style.display = `block`
    const cWidth = canvas.width * canvas.getZoom() / zoom
    const _width = fontObj.width * (cWidth/canvasInfo.width)
    cursor.style.width = `${_width}px`
    cursor.style.height = `${_width}px`
    cursor.style.left = `${options.e.clientX -_width/2}px`
    cursor.style.top = `${options.e.clientY - _width/2}px`
  }
  if (canvas.getZoom() === zoom) return
  if (options.e.button === 0 && isTranslation.value && moveInfo.value.isDown) { // 确保是左键拖动
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
  const cursor = document.getElementById('fabric-modal-cursor')
  cursor.style.display = `none`
};
const onMouseWheel = opt => {
  const delta = opt.e.deltaY; // 正值为放大
  let _zoom = canvas.getZoom();
  if (_zoom === zoom) zoomInfo.value = {offsetX: opt.e.offsetX, offsetY: opt.e.offsetY}
  _zoom *= 0.999 ** delta;
  if (_zoom > 20) _zoom = 20;
  if (_zoom < zoom) _zoom = zoom;
  canvas.zoomToPoint({x: zoomInfo.value.offsetX, y: zoomInfo.value.offsetY}, _zoom); // 以鼠标指针来缩放画板
  if(canvas.isDrawingMode&&drawType.value==='draw') {
    canvas.freeDrawingBrush.width = fontObj.width;
    const cursor = document.getElementById('fabric-modal-cursor')
    const cWidth = canvas.width * canvas.getZoom() / zoom
    const _width = fontObj.width * (cWidth/canvasInfo.width)
    cursor.style.width = `${_width}px`
    cursor.style.height = `${_width}px`
  }
  if (_zoom === zoom) {
    canvas.viewportTransform[4] = 0
    canvas.viewportTransform[5] = 0
    moveInfo.value.isDown = false
    isTranslation.value = false
    canvas.isDrawingMode = true;
    drawType.value = 'draw'
    canvas.requestRenderAll(); // 异步更新画板，提升性能
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
  // if (canvas.getZoom() !== zoom) return
  if (opt.target) {
    if (operateListIndex.value < operateList.value.length - 1) {
      operateList.value.splice(operateListIndex.value + 1);
    }
    operateList.value.push({
      canvas: JSON.stringify(canvas), canvasInfo: {
        ...canvasInfo,
        zoom: zoom,
        initUrl: initUrl.value
      }
    });// 将操作存在记录里
    operateListIndex.value = operateList.value.length - 1;
  }
};
const imageUrlClip = (url) => {
  if (url && clipType.value === 'init') {
    resetUrl.value = url
    emit('change', url)
    afterClose()
    visible.value = false;
    loading.value = false
    return
  }
  drawType.value = 'draw'
  init(url)
}
const prevDraw = () => {
  if (operateListIndex.value > 0) {
    let index = operateListIndex.value - 1;
    operateListIndex.value = index;
    // arr canvas对象
    canvasInfo = operateList.value[index].canvasInfo
    zoom = operateList.value[index].canvasInfo.zoom
    initUrl.value = operateList.value[index].canvasInfo.initUrl
    canvas.loadFromJSON(operateList.value[index].canvas);
    canvas.setWidth(canvasInfo.canvasWidth);
    canvas.setHeight(canvasInfo.canvasHeight);
    canvas.setZoom(zoom);
    lockObj(canvas,'his')
  }
};
const nextDraw = () => {
  if (operateListIndex.value < operateList.value.length - 1) {
    let index = operateListIndex.value + 1;
    operateListIndex.value = index;
    canvasInfo = operateList.value[index].canvasInfo
    zoom = operateList.value[index].canvasInfo.zoom
    initUrl.value = operateList.value[index].canvasInfo.initUrl
    canvas.loadFromJSON(operateList.value[index].canvas);
    canvas.setWidth(canvasInfo.canvasWidth);
    canvas.setHeight(canvasInfo.canvasHeight);
    canvas.setZoom(zoom);
    lockObj(canvas,'his')
  }
};
const removeImageCanvas = () => {
  for (let item of canvas.getObjects()) {
    if (item.type === 'image') {
      canvas.remove(item);
    }
  }
}
const hasFreeDraw = (arr) => {
  let flag = false;
  for (let item of canvas.getObjects()) {
    if (item.type === 'path') {
      flag = true
      break;
    }
  }
  return flag
}
const lockObj = (arr,type) => {
  setTimeout(function () {
    // canvas.setWidth(canvasInfo.canvasWidth);
    // canvas.setHeight(canvasInfo.canvasHeight);
    // canvas.setZoom(canvasInfo.zoom);
    arr.getObjects().forEach(function (item) {
      item.lockMovementX = true; // 禁止水平移动
      item.lockMovementY = true; // 禁止垂直移动
      item.hasRotatingPoint = false; // 无旋转点
      item.hasControls = false; // 编辑框
      item.selectable = false; // 不可选中
    });
    if(type==='his'){
      canvas.zoomToPoint({x: 0, y: 0}, zoom); // 以鼠标指针来缩放画板
      canvas.viewportTransform[4] = 0
      canvas.viewportTransform[5] = 0
      canvas.requestRenderAll(); // 异步更新画板，提升性能
    }
    // limitOutOfRange()
  }, 0);
}
const clip = () => {
  drawType.value = 'clip'
  nextTick(() => {
    if (initUrl.value) {
      // canvas.setWidth(canvasInfo.width);
      // canvas.setHeight(canvasInfo.height);
      // canvas.setZoom(1);
      // const base64Image = canvas.toDataURL("image/png");
      //  if(canvas){
      //    lastCanvas.value = {
      //      canvasInfo: canvasInfo,
      //      zoom: zoom,
      //      canvas: JSON.stringify(canvas),
      //      initUrl: initUrl.value
      //    }
      //  }
      ClipViewRef.value.showClip(initUrl.value)
    }
  })
};
const tabDraw = () => {
  canvas.isDrawingMode = true;
  isTranslation.value = false
};
const tabTranslation = () => {
  if (zoom === canvas.getZoom()) {
    message.info('请先滚轮放大后再平移')
    return
  }
  canvas.isDrawingMode = false;
  isTranslation.value = true
  canvas.selection = false; // 禁用选择框，使拖动更加直观
  canvas.forEachObject(function (o) {
    o.selectable = false;
  });
};
const reset = () => {
  drawType.value = 'draw'
  init(resetUrl.value)
};
const resetToParent = () => {
  if (canvas) {
    const url = resetUrl.value
    canvasClear()
    emit('change', url)
  }
};
const handleClip = () => {
  ClipViewRef.value.handleOk()
};
const cancelClip = () => {
  if (clipType.value === 'init') {
    cancel()
    return
  }
  drawType.value = 'draw'
  let url = clipUrl.value || resetUrl.value
  if (canvas) {
    footerToolRef.value.setFormValue(fontObj, 'draw')
    // if (lastCanvas.value && lastCanvas.value.canvasInfo) {
    //   edtInit(url)
    // }
    // canvas.setWidth(canvasInfo.canvasWidth);
    // canvas.setHeight(canvasInfo.canvasHeight);
    // canvas.setZoom(zoom);
    // drawType.value = 'draw'
    canvas.setWidth(canvasInfo.canvasWidth);
    canvas.setHeight(canvasInfo.canvasHeight);
    canvas.setZoom(zoom);
    limitOutOfRange()
  } else {
    // drawType.value = 'draw'
    nextTick(() => {
      footerToolRef.value.setFormValue(fontObj, 'draw')
      init(url)
    })
  }
};
defineExpose({
  showClip,
  clearHistoryList,
  resetToParent,
  cancel
})
</script>
<style scoped lang="less">
.image-edt-modal {
  .title {
    line-height: 30px;
    padding-right: 20px;
  }

  .tips {
    line-height: 30px;
    color: #ff0000;
  }

  .canvas-content {
    height: calc(80vh - 192px);
    overflow: hidden;
  }

  .coarse-fine {
    width: 320px;
    padding: 0 20px;
    background-color: #2F2F2F;
    border-radius: 20px;
  }

  .footer-btn {
    margin-bottom: 30px;

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
        }

        .disabled {
          color: #5e5959;
        }
      }
    }
  }
}
</style>
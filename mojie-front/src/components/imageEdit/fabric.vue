<template>
  <a-modal class="image-edt-modal" :maskClosable="false" v-model:visible="visible" :destroyOnClose="true"
           title="迁移替换" @ok="handleOk"
           width="80%">
    <div class="flex justify-center items-center">
      <canvas id="fabric-canvas"/>
    </div>
    <template #footer>
      <div class="flex">
        <div class="coarse-fine mr-10">
          <FooterTool ref="footerToolRef" @change="toolChange"></FooterTool>
        </div>
        <div class="image-btn flex mr-10">
          <div class="flex-1">
            <i class="iconfont icon-huabi1" title="画笔"></i><br>
          </div>
          <div class="flex-1">
            <i class="iconfont icon-caijian1" title="裁剪"></i><br>
          </div>
          <div class="flex-1">
            <i class="iconfont icon-zhongzhi3"  title="还原"></i><br>
          </div>
        </div>
        <div class="image-btn his flex mr-10">
          <div class="flex-1">
            <i class="iconfont icon-weibiaoti545"  title="上一步" @click="prevDraw"></i><br>
          </div>
          <div class="flex-1">
            <i class="iconfont icon-weibiaoti546"  title="下一步"  @click="nextDraw"></i><br>
          </div>
        </div>
        <div class="flex-1">
        </div>
        <div>
          <a-button type="primary" @click="handleOk">
            <template #icon><check-outlined /></template>
            完成涂抹
          </a-button>
        </div>
      </div>
    </template>
  </a-modal>
</template>
<script setup>
import FooterTool from "@/components/imageEdit/footerTool.vue";

import {CheckOutlined} from '@ant-design/icons-vue';
import {defineEmits, nextTick, reactive,defineExpose, ref} from 'vue';
import {fabric} from "fabric";

const visible = ref(false);
const footerToolRef = ref();
const drawType = ref('text');
const size = ref(30);
const color = ref('#000000');
let canvas = null;
let zoom = 1;
let canvasInfo = {}
let dialogStyle = {
   background:'#fff'
}
const emit = defineEmits(['change']);
const fontObj = reactive({
  width: 100
})

// 绘制对象
let textArr = [];
//操作记录
let operateList = []
let operateListIndex = 0
// 当前绘制对象坐标
let points = [];
const handleOk = e => {
  if (canvas) {
    canvas.setWidth(canvasInfo.width);
    canvas.setHeight(canvasInfo.height);
    canvas.setZoom(1);
    const base64Image = canvas.toDataURL("image/png");
    emit('change', base64Image)
   //  canvasClear()
  }
  visible.value = false;
};
const cancel = e => {
  visible.value = false;
};
const canvasClear = () => {
  canvas.clear(); // 这个方法实际上是移除所有对象并清除背景的快捷方式
// 删除画布元素（可选）
  canvas = null;
};
const showClip = (url, str) => {
  visible.value = true;
  drawType.value = str;
  if (!str) return
  nextTick(() => {
    footerToolRef.value.setFormValue(fontObj,'draw')
    init(url)
  })
};
const toolChange = (obj) => {
  fontObj.width = obj.width
  if(drawType.value === 'draw') {
    // canvas.freeDrawingBrush.color = obj.color;
    canvas.freeDrawingBrush.width = obj.width;
  } else {

  }
}
const clearHistoryList = () => {
  operateList = []
  canvasClear()
}

const init = async (url) => {
  const imageInfo = await initCanvasSize(url)
  await initCas(imageInfo.zoom);
  await imageAddCanvas(imageInfo)
  // 注册画布事件
  initEvent();
  operateList.push(JSON.stringify(canvas));// 将操作存在记录里
  operateListIndex = operateList.length - 1;
  if (drawType.value !== "text") {
    freeDraw()
  }
};
// 初始化画布尺寸
const initCanvasSize = (url) => {
  var canvasEle = document.getElementById('fabric-canvas')
  return new Promise(function (resolve) {
    var imaged = new Image()
    imaged.crossOrigin = 'Anonymous'
    imaged.src = url
    imaged.onload = function () {
      let width = imaged.width
      let height = imaged.height
      let r = height / width
      let maxWidth = document.body.offsetWidth * 0.8 - 48
      let maxHeight = document.body.offsetHeight * 0.8 - 148
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
      canvasInfo = {
        width: imaged.width,
        height: imaged.height
      }
    }
  })
}
const imageAddCanvas = (imageInfo) => {
  return new Promise(function (resolve) {
    let left = 0
    let top = 0
    var imaged = new fabric.Image(imageInfo.imaged, {
      cornerStyle: 'circle',
      cornerStrokeColor: 'blue',
      cornerColor: 'blue',
      cornerSize: 13,
      left,
      top
    })
    canvas.add(imaged)
    imaged.selectable = false;
    resolve(canvas)
  })
}
const initCas = () => {
  return new Promise(function (resolve) {
    canvas = new fabric.Canvas("fabric-canvas", {backgroundColor: '#ffffff'});
    // 初始化画布状态
    canvas.hasDraw = false;
    canvas.setZoom(zoom);
    canvas.zoom = zoom;
    resolve(canvas)
  })
};
const initEvent = () => {
  canvas.on("mouse:up", onMouseUp);
};
//画笔
const freeDraw = (e) => {
  canvas.isDrawingMode = true;
  if(fabric.PatternBrush) {
    //设置黑白格画笔
    const squarePatternBrush = new fabric.PatternBrush(canvas);
    squarePatternBrush.getPatternSrc = function() {

      const squareWidth = 10, squareDistance = 10;

      const patternCanvas = fabric.document.createElement('canvas');
      patternCanvas.width = patternCanvas.height = squareWidth + squareDistance;
      const ctx = patternCanvas.getContext('2d');

      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, squareWidth, squareWidth);
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 10, squareWidth, squareWidth);
      ctx.fillStyle = '#000000';
      ctx.fillRect(10, 0, squareWidth, squareWidth);
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(10, 10, squareWidth, squareWidth);
      return patternCanvas;
    };
    canvas.freeDrawingBrush = squarePatternBrush;

    canvas.freeDrawingBrush.width = fontObj.width;
    if (canvas.freeDrawingBrush) {
      const brush = canvas.freeDrawingBrush;
      brush.color = '#000000';
      if (brush.getPatternSrc) {
        brush.source = brush.getPatternSrc.call(brush);
      }
      brush.width = parseInt( fontObj.width, 10) || 1;
      brush.shadow = new fabric.Shadow({
        blur: parseInt(30, 10) || 0,
        offsetX: 0,
        offsetY: 0,
        affectStroke: true,
        color: "#ffffff",
      });
    }
  }
};
const onMouseUp = opt => {
  if (opt.target) {
    if(operateListIndex < operateList.length -1 ) {
      operateList.splice(operateListIndex+1);
    }
    operateList.push(JSON.stringify(canvas));// 将操作存在记录里
    operateListIndex = operateList.length - 1;
  }
};

//滚轮缩放图片
const onMouseWheel = opt => {
  let delta = opt.e.deltaY;
  let _zoom = canvas.getZoom();
  _zoom *= 0.999 ** delta;
  if (_zoom > 20) zoom = 20;
  if (_zoom < 0.01) zoom = 0.01;
  canvas.setZoom(_zoom);
  canvas.zoom = _zoom;
};
const prevDraw = () => {
  if (operateListIndex > 0) {
    let index = operateListIndex - 1;
    operateListIndex = index;
    canvas.loadFromJSON(operateList[index]);
    lockObj(canvas);
  }
};
const nextDraw = () => {
  if ( operateListIndex < operateList.length - 1) {
    let index = operateListIndex + 1;
    operateListIndex = index;
    canvas.loadFromJSON(operateList[index]);
    lockObj(canvas);
  }
};
const lockObj = (arr) =>{
  // arr canvas对象
  setTimeout(function () {
    arr.getObjects().forEach(function (item) {
      item.lockMovementX = true; // 禁止水平移动
      item.lockMovementY = true; // 禁止垂直移动
      item.hasRotatingPoint = false; // 无旋转点
      item.hasControls = false; // 编辑框
      item.selectable = false; // 不可选中
    });
  }, 0);
}
defineExpose({
  showClip,
  clearHistoryList
})
</script>
<style scoped lang="less">
.coarse-fine{
  width: 320px;
  margin-bottom: 30px;
  padding: 0 20px;
  background-color: #2F2F2F;
  border-radius: 20px;
}
.image-btn{
  width: 150px;
  padding:6px;
  height: 32px;
  font-size: 12px;
  text-align: center;
  color: #787878;
  border-radius: 20px;
  background-color: #303030;
  &.his{
    width: 100px;
  }
  >.flex-1{
    line-height: 20px;
    .iconfont{
      font-size: 16px;
      cursor: pointer;
    }
  }
}
</style>
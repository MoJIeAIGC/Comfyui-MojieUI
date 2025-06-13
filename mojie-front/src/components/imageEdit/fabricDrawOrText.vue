<template>
  <a-modal :maskClosable="false" v-model:visible="visible" :destroyOnClose="true"
           :title="drawType==='text'? '添加文本':'涂鸦'" @ok="handleOk"
           width="80%">
    <div class="flex justify-center items-center">
      <canvas id="fabric-canvas"/>
    </div>
    <template #footer>
      <div class="flex">
        <FooterTool ref="footerToolRef" @change="toolChange"></FooterTool>
        <div v-if="drawType==='text'" class="mr-10">
          <a-button type="primary" @click="drawText">添加文本</a-button>
        </div>
        <div class="mr-10">
          <a-button type="primary" @click="prevDraw">上一步</a-button>
          <a-button type="primary" @click="nextDraw">下一步</a-button>
        </div>
        <div>
          <a-button @click="cancel" type="primary">取消</a-button>
          <a-button type="primary" @click="handleOk">保存</a-button>
        </div>
      </div>
    </template>
  </a-modal>
</template>
<script setup>
import FooterTool from "@/components/imageEdit/footerTool.vue";
// 图片裁剪
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
const emit = defineEmits(['change']);
const fontObj = reactive({
  fontSize: 36,
  fill: '#F80000',
  width: 36,
  color: '#F80000'
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
    console.log(base64Image)
    emit('change', base64Image)
    canvasClear()
  }
  visible.value = false;
};
const cancel = e => {
  console.log(canvas)
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
    footerToolRef.value.setFormValue(fontObj,str)
    init(url)
  })
};
const toolChange = (obj) => {
  fontObj.width = obj.width
  fontObj.color = obj.color
  fontObj.fontSize = obj.fontSize
  fontObj.fill = obj.fill
  if(drawType.value === 'draw') {
    // canvas.freeDrawingBrush.color = obj.color;
    canvas.freeDrawingBrush.width = obj.width;
  } else {
      let activeObject = canvas.getActiveObject();
      if (activeObject instanceof fabric.Textbox) {
        activeObject.set('borderColor', obj.fill)
        activeObject.set('fill', obj.fill)
        activeObject.set('fontSize', obj.fontSize)
        canvas.add(activeObject);
      } else {
        console.log('No Textbox selected');
      }
  }
}
const init = async (url) => {
  const imageInfo = await initCanvasSize(url)
  await initCas(imageInfo.zoom);
  await imageAddCanvas(imageInfo)
  operateList = []
  // 注册画布事件
  initEvent();
  operateList.push(JSON.stringify(canvas));// 将操作存在记录里
  operateListIndex = operateList.length - 1;
  if (drawType.value !== "text") {
    freeDraw()
  } else {
    drawText()
  }
};
// 初始化画布尺寸
const initCanvasSize = (url) => {
  var canvasEle = document.getElementById('fabric-canvas')
  return new Promise(function (resolve, reject) {
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
    canvas = new fabric.Canvas("fabric-canvas", {
      // preserveObjectStacking: true,
      // centeredRotation: true,
      backgroundColor: '#ffffff',
      // selection: false // 取消框选
      //isDrawingMode:true,
      // skipTargetFind: true,
      // selectable: false, //对象选择
      // skipTargetFind: true // 画板元素不能被选中
    });
    // 初始化画布状态
    canvas.hasDraw = false;
    canvas.setZoom(zoom);
    canvas.zoom = zoom;
    resolve(canvas)
  })
};
const initEvent = () => {
  canvas.on("mouse:up", onMouseUp);
  // canvas.on("mouse:down", onMouseDown);
  // canvas.on("mouse:move", onMouseMove);
  // canvas.on("mouse:wheel", onMouseWheel);
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
//添加文字
const drawText = () => {
  canvas.isDrawingMode = false;
  canvas.isDragging = false;
  let textbox = new fabric.Textbox("输入文字", {
    width: 250,
    top: 10 + textArr.length * 30,
    left: 10 + textArr.length * 30,
    borderColor: fontObj.fill,
    fill: fontObj.fill,
    fontSize: fontObj.fontSize,
    hasControls: true,
    lockRotation: true
  });
  textArr.push(textbox)
  canvas.add(textbox);
  canvas.hasDraw = true;
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
const onMouseMove = options => {
    if (canvas._currentTransform) return; // 如果正在变换，则不处理移动事件
    var pointer = canvas.getPointer(options.e);
    var activeObject = canvas.getActiveObject();
    if (activeObject && activeObject.type === 'line' && options.e.shiftKey) {
      activeObject.set({ x2: pointer.x, y2: pointer.y }); // 更新线条终点位置
      canvas.renderAll(); // 重新渲染画布
    }
};
const onMouseDown = options => {
  var pointer = canvas.getPointer(options.e);
  var path = new fabric.Line([pointer.x, pointer.y, pointer.x, pointer.y], {
    stroke: '#000000', // 线条颜色
    strokeWidth: 5, // 线条宽度
    selectable: true, // 是否可选
    evented: true // 是否响应事件
  });
  canvas.add(path);
  canvas.renderAll(); // 重新渲染画布
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
//文本移动位置
const resizePos = opt => {
  let vpt = canvas.viewportTransform;
  let spaceX = -vpt[4];
  let spaceY = -vpt[5];
  let offsetX = opt.e.offsetX + spaceX;
  let offsetY = opt.e.offsetY + spaceY;
  if (canvas.zoom >= 1) {
    offsetX = offsetX / canvas.zoom;
    offsetY = offsetY / canvas.zoom;
  } else {
    offsetX = offsetX * (1 / canvas.zoom);
    offsetY = offsetY * (1 / canvas.zoom);
  }
  let point = {
    x: offsetX,
    y: offsetY
  };
  return point;
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
    arr.getObjects().forEach(function (item, index) {
      item.lockMovementX = true; // 禁止水平移动
      item.lockMovementY = true; // 禁止垂直移动
      item.hasRotatingPoint = false; // 无旋转点
      item.hasControls = false; // 编辑框
      item.selectable = false; // 不可选中
    });
  }, 0);
}
defineExpose({
  showClip
})
</script>
<style scoped lang="less">

</style>
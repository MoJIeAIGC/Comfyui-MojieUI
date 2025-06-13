<template>
  <div class="flex flex-col">
    <div class="flex-1 h-0-o-a">
      <div class="tool-content">
        <div class="operate-image">
          <div class="image-view up-box flex justify-center items-center" :class="drapClass" v-if="!imageUrl">
            <div class="up-btn flex items-center justify-center"  @click="uploadFile"
                 @drop.prevent="handleDrop" @dragover.prevent="drapClassChange('over')"
                 @dragenter.prevent="drapClassChange('enter')" @dragleave="drapClassChange('leave')">
              <div class="text-center">
                <PlusOutlined :style="{fontSize: '26px'}"/>
                <div class="ant-upload-file-tips">添加图片(支持拖拽添加)</div>
              </div>
            </div>
          </div>
          <div class="image-view" v-if="imageUrl" :class="drapClass" ref="imageViewRef"  @drop.prevent="handleDrop" @dragover.prevent="drapClassChange('over')"
               @dragenter.prevent="drapClassChange('enter')" @dragleave="drapClassChange('leave')">
            <close-circle-filled class="close-img" @click="clearImage"/>
            <div class="bg-wrap no-select" ref="refBgWrap"
                 :style="{ width: _data.dragInfo.width + 'px', height: _data.dragInfo.height + 'px',top: _data.dragInfo.top + 'px', left: _data.dragInfo.left + 'px' }">
              <div class="img-role-wrap" ref="refRoleWrap"
                   :style="{ 'left': innerStyle.left + 'px', 'top': innerStyle.top + 'px', width: innerStyle.width + 'px', height: innerStyle.height + 'px'}">
                <img :src="imageUrl" :style="{  width: innerStyle.width + 'px', height: innerStyle.height + 'px' }"
                     class="img-role" @mousedown.stop="mousedownFn" draggable="false"/>
              </div>
              <span class="span-dot" :class="item" @mousedown.stop="scale(item)" v-for="(item, index) in direction"
                    :key="index"></span>
              <span v-if="tabIndex==='2'" class="span-dot" :class="item" @mousedown.stop="scale(item)"
                    v-for="(item, index) in tabDirection" :key="index"></span>
            </div>
          </div>
        </div>
      </div>
      <div class="collapse-box">
        <div>
          <div class="flex collapse-content-title">
            <div class="tab-item flex-1" :class="{active: tabIndex === '1'}" @click="tabIndexChange('1')">画幅扩展</div>
            <div class="tab-item flex-1" :class="{active: tabIndex === '2'}" @click="tabIndexChange('2')">自定义扩展
            </div>
          </div>
          <div v-if="tabIndex==='1'" class="mt-20">
            <div class="fixed-item" v-for="item in _data.list" :key="item.type"
                 :class="{active:item.id === _data.dragInfo.id}" @click="dragViewChange(item)">
              <div class="fixed-box flex justify-center items-center">
                <div class="text-center">
                  <i :class="'iconfont ' + item.icon"></i><br>
                  {{ item.type }}
                </div>
              </div>
            </div>
          </div>
          <div v-if="tabIndex==='2'" class="mt-20 customize">
            <div class="top-item flex justify-center items-center">
              <div class="text-center">
                <div class="item-input">
                  <a-input-number class="ipt" :min="0" v-model:value="oForm.top" @change="formChange('top')" :max="3000"
                                  addonAfter="像素"/>
                </div>
                <div>
                  <up-circle-filled style="fill: #FFFFFF"/>
                </div>
              </div>
            </div>
            <div class="left-right-item flex">
              <div class="flex-1">
                <div class="flex justify-center items-center">
                  <div class="item-input">
                    <a-input-number class="ipt" :min="0" v-model:value="oForm.left" @change="formChange('left')"
                                    :max="3000" addonAfter="像素"/>
                  </div>
                  <left-circle-filled style="fill: #FFFFFF"/>
                </div>
              </div>
              <div class="flex-1">
                <div class="text-center flex justify-center items-center">
                  <right-circle-filled style="fill: #FFFFFF"/>
                  <div class="item-input">
                    <a-input-number class="ipt" :min="0" v-model:value="oForm.right" @change="formChange('right')"
                                    :max="3000" addonAfter="像素"/>
                  </div>
                </div>
              </div>
            </div>
            <div class="down-item flex justify-center items-center">
              <div class="text-center">
                <div>
                  <down-circle-filled style="fill: #FFFFFF"/>
                </div>
                <div class="item-input">
                  <a-input-number class="ipt" :min="0" v-model:value="oForm.bottom" @change="formChange('bottom')"
                                  :max="3000" addonAfter="像素"/>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="bottom-btn">
      <a-button type="primary" size="large" shape="round" class="send-btn items-center justify-center" :disabled="isDis"
                @click="submit" :loading="_data.loading">
        <template #icon>
          <i class="iconfont icon-a-ziyuan19"></i>
        </template>
        立即生成（{{ pointText }}）
      </a-button>
      <!--      <div class="add-btn">-->
      <!--        <i class="iconfont icon-a-ziyuan19"></i>-->
      <!--        <span>立即生成（消耗5算力）</span>-->
      <!--      </div>-->
    </div>
  </div>
</template>
<script setup>

import {onMounted, reactive, ref, onUnmounted, defineProps, defineEmits, computed, defineExpose} from "vue";
import {
  UpCircleFilled,
  DownCircleFilled,
  LeftCircleFilled,
  RightCircleFilled,
  CloseCircleFilled, PlusOutlined
} from "@ant-design/icons-vue";
import {delUploadImg, uploadImg} from "@/api/upload.js";
import {useUserStore} from "@/store/userStore.js";
import {useImageExpend} from "@/api/product.js";
import {base64UrlToFile, convertImgToBase64, isImageFile, compressFile, isHttp} from "@/utils/utils.js";
import {message} from "ant-design-vue";
import emitter from "@/utils/emitter.js";
import {deductionRules, httpIndex} from "@/options/model.js";

const emit = defineEmits(['change', 'no-points']);
const userStore = useUserStore()
const imageUrl = ref('')
const pixelRatio = ref(1) //像素比
const tabRatio = ref(1) //自定义拖动框的长宽比
const oForm = reactive({
  left: 0,
  top: 0,
  right: 0,
  bottom: 0
})
const _data = reactive({
  loading: false,
  timer: null,
  timer2: null,
  uploadInfo: {},
  active: {id: 1, icon: 'icon-bili', type: '1:1', width: 320, height: 320, top: 30, left: 30},
  dragInfo: {id: 1, icon: 'icon-bili', type: '1:1', width: 320, height: 320, top: 30, left: 30},
  imageInfo: {width: 320, height: 320, top: 0, left: 0, maxLeft: 0, maxTop: 0},
  list: [
    {id: 0, icon: 'icon-crop--', type: '16:9', width: 320, height: 180, top: 100, left: 30},
    {id: 1, icon: 'icon-list-choice-', type: '1:1', width: 320, height: 320, top: 30, left: 30},
    {id: 2, icon: 'icon-a-3bi4', type: '3:4', width: 240, height: 320, top: 30, left: 70},
    {id: 3, icon: 'icon-a-16bi9', type: '9:16', width: 180, height: 320, top: 30, left: 100}
  ],
})

const props = defineProps({
  chatId: {
    type: [String, Number],
    default: ''
  }
})
const innerStyle = ref({
  left: 0,
  top: 0,
  width: 100,
  height: 0
})
const isDis = computed(() => {
  if (_data.loading) return _data.loading
  return false
});
const _deductionRules = computed(() => {
  const isVip = userStore.vipInfo&&userStore.vipInfo.level
  return  isVip ? deductionRules.vip : deductionRules.default
});
const pointText = computed(() => {
  const isVip = userStore.vipInfo&&userStore.vipInfo.level
  if(_deductionRules.value.flex === 0 &&isVip)  return '会员免费'
  return  '消耗'+_deductionRules.value.flex +'算力'
});
const isDrag = ref(false)
const isScale = ref(false)
const imageViewRef = ref()
const refBgWrap = ref()
const refRoleWrap = ref()
const direction = ref(['left-top', 'right-top', 'left-bottom', 'right-bottom'])
const tabDirection = ref(['top', 'right', 'left', 'bottom'])
const directionType = ref('')
onMounted(() => {
  emitter.on('extend-mousemove',mousemove)
  emitter.on('extend-mouseup',mouseup)
})

onUnmounted(() => {
  emitter.off('extend-mousemove')
  emitter.off('extend-mouseup')
  if (_data.timer) clearTimeout(_data.timer)
  if (_data.timer2) clearTimeout(_data.timer2)
})
const drapClass = ref('')
const drapClassChange = (type) => {
  drapClass.value = type
}
const handleDrop = (event) => {
  drapClass.value = ''
  let url = event.dataTransfer.getData('text/plain'); // 获取数据
  if (url) {
    if(isHttp(url) &&url.indexOf(httpIndex)===-1){
      message.error('您拖拽的图片链接非本网站的链接，请先下载后再拖入下载后的图片')
      return
    }
    clearImage()
    initUrl(url)
    return;
  }
  const files = event.dataTransfer.files;
  if (files.length > 1) return message.warning("只能拖入一个文件")
  if (files.length === 1) {
    if (isImageFile(files[0].type)) {
      clearImage()
      previewFile(files[0])
    } else {
      message.warning("拖入的文件不是图片格式")
    }
  }
}
const initUrl = (url) => {
  convertImgToBase64(url, (base64) => {
    clearImage()
    const draFile = base64UrlToFile(base64)
    previewFile(draFile)
  })
}
const mousemove = (e) => {
  if (!refRoleWrap.value) return;
  if (isScale.value) {  //缩放
    const {movementX, movementY} = e
    const {width: minWidth, height: minHeight} = refRoleWrap.value.getBoundingClientRect()
    let x = Number(_data.dragInfo.left) + movementX
    let y = Number(_data.dragInfo.top) + movementY
    let roleRatio = tabIndex.value === '2' ? _data.imageInfo.width / _data.imageInfo.height : _data.active.width / _data.active.height //原始role图片分辨率比例
    switch (directionType.value) {
      case 'left-top':
        //改变x+y+width+height
        const _width = _data.dragInfo.width - movementX
        const _height = _data.dragInfo.height - movementX / roleRatio
        if (_width >= minWidth && _height >= minHeight) {
          _data.dragInfo.width = _width
          _data.dragInfo.height = _height
          _data.dragInfo.left = x
          _data.dragInfo.top = y
        }
        break
      case 'right-top':
        //改变y+width+height
        const rt_width = _data.dragInfo.width + movementX
        const rt_height = _data.dragInfo.height + movementX / roleRatio
        if (rt_width >= minWidth && rt_height >= minHeight) {
          _data.dragInfo.width = rt_width
          _data.dragInfo.height = rt_height
          _data.dragInfo.top = y
        }
        break
      case 'left-bottom':
        //改变x+width+height
        const lb_width = _data.dragInfo.width - movementX
        const lb_height = _data.dragInfo.height - movementX / roleRatio
        if (lb_width >= minWidth && lb_height >= minHeight) {
          _data.dragInfo.width = lb_width
          _data.dragInfo.height = lb_height
          _data.dragInfo.left = x
        }
        break
      case 'right-bottom':
        //width+height
        const rb_width = _data.dragInfo.width + movementX
        const rb_height = _data.dragInfo.height + movementX / roleRatio
        if (rb_width >= minWidth && rb_height >= minHeight) {
          _data.dragInfo.width = rb_width
          _data.dragInfo.height = rb_height
        }
        break
      case 'top':
        //y + height
        const t_height = _data.dragInfo.height - movementY
        const _top = innerStyle.value.top - movementY
        if (t_height >= minHeight && _top >= 0) {
          _data.dragInfo.height = t_height
          _data.dragInfo.top = y
          innerStyle.value.top = _top
        }
        break
      case 'bottom':
        //height
        const b_height = _data.dragInfo.height + movementY
        if (b_height >= innerStyle.value.top + minHeight) {
          _data.dragInfo.height = b_height
        }
        break
      case 'left':
        //x + width
        const l_width = _data.dragInfo.width - movementX
        const _left = innerStyle.value.left - movementX
        if (l_width >= minWidth && _left >= 0) {
          _data.dragInfo.width = l_width
          _data.dragInfo.left = x
          innerStyle.value.left = _left
        }
        break
      case 'right':
        //width
        const r_width = _data.dragInfo.width + movementX
        if (r_width >= minWidth + innerStyle.value.left) {
          _data.dragInfo.width = r_width
        }
        break
    }
  }
  if (isDrag.value) { //移动图片
    const {width: bwidth, height: bheight} = refRoleWrap.value.getBoundingClientRect()
    const {width: awidth, height: aheight} = refBgWrap.value.getBoundingClientRect()
    const {movementX, movementY} = e
    let maxLeft = awidth - bwidth
    let maxTop = aheight - bheight
    let x = Number(innerStyle.value.left) + movementX
    let y = Number(innerStyle.value.top) + movementY
    if (x <= 0) {
      x = 0
    } else if (x >= maxLeft) {
      x = maxLeft
    }
    if (y <= 0) {
      y = 0
    } else if (y >= maxTop) {
      y = maxTop
    }
    pixelRatio.value = _data.imageInfo.width / bwidth
    innerStyle.value.left = x
    innerStyle.value.top = y
    oForm.left = numberFixed(x * pixelRatio.value)
    oForm.top = numberFixed(y * pixelRatio.value)
    oForm.right = numberFixed((maxLeft - x) * pixelRatio.value)
    oForm.bottom = numberFixed((maxTop - y) * pixelRatio.value)
  }
}
const numberFixed = (n) => {
  return Math.round(n)
}
const mouseup = () => {
  if (isScale.value) {
    if (tabIndex.value === '2') {//自定义扩展
      if (tabDirection.value.indexOf(directionType.value) !== -1) tabRatio.value = _data.dragInfo.width / _data.dragInfo.height
      const imageRatio = tabRatio.value
      const maxWidth = 320
      const maxHeight = 320
      const roleRatio = maxWidth / _data.dragInfo.width
      const roleRatio_h = maxHeight / _data.dragInfo.height
      const _width = imageRatio > 1 ? maxWidth : maxHeight * imageRatio
      const _height = imageRatio > 1 ? maxWidth / imageRatio : maxHeight
      _data.dragInfo = JSON.parse(JSON.stringify({
        width: _width,
        height: _height,
        top: (380 - _height) / 2,
        left: (380 - _width) / 2,
      }))
      if (imageRatio > 1) {
        innerStyle.value.width = innerStyle.value.width * roleRatio
        innerStyle.value.height = innerStyle.value.height * roleRatio
        innerStyle.value.top = innerStyle.value.top * roleRatio
        innerStyle.value.left = innerStyle.value.left * roleRatio
      } else {
        innerStyle.value.width = innerStyle.value.width * roleRatio_h
        innerStyle.value.height = innerStyle.value.height * roleRatio_h
        innerStyle.value.top = innerStyle.value.top * roleRatio_h
        innerStyle.value.left = innerStyle.value.left * roleRatio_h
      }
      if (tabDirection.value.indexOf(directionType.value) === -1 && innerStyle.value.width + innerStyle.value.left > _data.dragInfo.width) innerStyle.value.left = 0
      if (tabDirection.value.indexOf(directionType.value) === -1 && innerStyle.value.height + innerStyle.value.top > _data.dragInfo.height) innerStyle.value.top = 0
    } else {//画幅扩展
      const roleRatio = _data.active.width / _data.dragInfo.width
      _data.dragInfo = JSON.parse(JSON.stringify(_data.active))
      innerStyle.value.width = innerStyle.value.width * roleRatio
      innerStyle.value.height = innerStyle.value.height * roleRatio
      if (innerStyle.value.width + innerStyle.value.left > _data.dragInfo.width) innerStyle.value.left = 0
      if (innerStyle.value.height + innerStyle.value.top > _data.dragInfo.height) innerStyle.value.top = 0
    }

    pixelRatio.value = _data.imageInfo.width / innerStyle.value.width
    //计算上下前后距离并转成像素
    oForm.left = numberFixed(innerStyle.value.left * pixelRatio.value)
    oForm.top = numberFixed(innerStyle.value.top * pixelRatio.value)
    oForm.right = numberFixed((_data.dragInfo.width - innerStyle.value.width - innerStyle.value.left) * pixelRatio.value)
    oForm.bottom = numberFixed((_data.dragInfo.height - innerStyle.value.height - innerStyle.value.top) * pixelRatio.value)
  }
  isDrag.value = false
  isScale.value = false
}
const mousedownFn = () => {
  isDrag.value = true
  isScale.value = false
}
const scale = (val) => {
  directionType.value = val
  isScale.value = true
  isDrag.value = false
}
const tabIndex = ref('1')

const countImage = () => {
  let width = _data.imageInfo.width
  let height = _data.imageInfo.height
  let r = height / width
  let maxWidth = _data.active.width
  let maxHeight = _data.active.height
  _data.dragInfo = JSON.parse(JSON.stringify(_data.active))
  let cHeight = maxWidth * r
  if (cHeight > maxHeight) {
    let rh = width / height
    innerStyle.value.width = maxHeight * rh
    innerStyle.value.height = maxHeight
    innerStyle.value.left = (maxWidth - maxHeight * rh) / 2
    innerStyle.value.top = 0
    pixelRatio.value = height / maxHeight

    oForm.left = numberFixed((maxWidth - maxHeight * rh) * pixelRatio.value / 2)
    oForm.top = 0
    oForm.right = numberFixed((maxWidth - maxHeight * rh) * pixelRatio.value / 2)
    oForm.bottom = 0
  } else {
    innerStyle.value.width = maxWidth
    innerStyle.value.height = cHeight
    innerStyle.value.left = 0
    innerStyle.value.top = (maxHeight - cHeight) / 2
    pixelRatio.value = width / maxWidth
    oForm.left = 0
    oForm.top = numberFixed(Math.round((maxHeight - cHeight) * pixelRatio.value / 2))
    oForm.right = 0
    oForm.bottom = numberFixed(Math.round((maxHeight - cHeight) * pixelRatio.value / 2))
  }
}
//自定义计算
const customizeImage = () => {
  let width = _data.imageInfo.width
  let height = _data.imageInfo.height
  let r = height / width
  tabRatio.value = width / height
  let maxWidth = 320
  let maxHeight = 320
  let cHeight = maxWidth * r
  if (cHeight > maxHeight) {
    let rh = width / height
    innerStyle.value.width = maxHeight * rh
    innerStyle.value.height = maxHeight
    pixelRatio.value = height / maxHeight
  } else {
    innerStyle.value.width = maxWidth
    innerStyle.value.height = cHeight
    innerStyle.value.left = 0
    innerStyle.value.top = 0
    pixelRatio.value = width / maxWidth
  }
  innerStyle.value.left = 0
  innerStyle.value.top = 0
  oForm.left = 0
  oForm.top = 0
  oForm.right = 0
  oForm.bottom = 0
  _data.dragInfo = JSON.parse(JSON.stringify({
    width: innerStyle.value.width,
    height: innerStyle.value.height,
    top: (380 - innerStyle.value.height) / 2,
    left: (380 - innerStyle.value.width) / 2
  }))
}
const dragViewChange = (item) => {
  _data.active = item
  _data.dragInfo = JSON.parse(JSON.stringify(item))
  countImage()
}
const tabIndexChange = (index) => {
  tabIndex.value = index
  if (index === '1') {
    _data.dragInfo = JSON.parse(JSON.stringify(_data.active))
    countImage()
  } else {
    customizeImage()
  }
}
const formChange = (type) => {
  // pixelRatio.value = _data.imageInfo.width / innerStyle.value.width
  //计算上下前后距离并转成像素
  const top = oForm.top / pixelRatio.value
  const left = oForm.left / pixelRatio.value
  const right = oForm.left / pixelRatio.value
  const bottom = oForm.bottom / pixelRatio.value
  const maxWidth = 320
  const maxHeight = 320
  let _width = innerStyle.value.width + left + right
  let _height = innerStyle.value.height + top + bottom
  tabRatio.value = _width / _height
  const imageRatio = tabRatio.value
  const roleRatio = maxWidth / _width
  const roleRatio_h = maxHeight / _height
  const c_width = imageRatio > 1 ? maxWidth : maxHeight * imageRatio
  const c_height = imageRatio > 1 ? maxWidth / imageRatio : maxHeight
  _data.dragInfo = JSON.parse(JSON.stringify({
    width: c_width,
    height: c_height,
    top: (380 - c_height) / 2,
    left: (380 - c_width) / 2,
  }))
  if (imageRatio > 1) {
    innerStyle.value.width = innerStyle.value.width * roleRatio
    innerStyle.value.height = innerStyle.value.height * roleRatio
    innerStyle.value.top = top * roleRatio
    innerStyle.value.left = left * roleRatio
  } else {
    innerStyle.value.width = innerStyle.value.width * roleRatio_h
    innerStyle.value.height = innerStyle.value.height * roleRatio_h
    innerStyle.value.top = top * roleRatio_h
    innerStyle.value.left = left * roleRatio_h
  }
  // if (innerStyle.value.width + innerStyle.value.left > _data.dragInfo.width) innerStyle.value.left = 0
  // if (innerStyle.value.height + innerStyle.value.top > _data.dragInfo.height) innerStyle.value.top = 0
  pixelRatio.value = _data.imageInfo.width / innerStyle.value.width
}
const previewFile = file => {
  compressFile(file, (newFile) => {
    fileToBase64(newFile)
  },'extend')
  // if (file.size > 3 * 1024 * 1024) {
  //   compressFile(file, (newFile) => {
  //     fileToBase64(newFile)
  //   })
  // } else {
  //   fileToBase64(file)
  // }
  return false
}
const uploadFile = () => {
  let fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = "image/*";
  fileInput.click();
  fileInput.onchange = (event) => {
    previewFile(event.target.files[0])
  }
}
const fileToBase64 = file => {
  uploadImage(file)
  let r = new FileReader();
  r.readAsDataURL(file);
  r.onload = () => { // 读取操作完成回调方法dragImageRef.value
    // that.$refs.canvas.upLoadImage(r.result);
    imageUrl.value = r.result
    const imageRole = new Image()
    imageRole.onload = () => {
      _data.imageInfo.width = JSON.parse(JSON.stringify(imageRole.width))
      _data.imageInfo.height = JSON.parse(JSON.stringify(imageRole.height))
      if (tabIndex.value === '1') {
        countImage()
      } else {
        tabRatio.value = imageRole.width / imageRole.height
        customizeImage()
      }
    }
    imageRole.src = r.result
  };
  return false
}

const clearImage = () => {
  imageUrl.value = ''
  if (_data.uploadInfo && _data.uploadInfo.img_id) delUploadImg(_data.uploadInfo.img_id)
  _data.uploadInfo = ''
}
const uploadImage = async (file, type) => {
  const fileData = new FormData();
  fileData.append('image', file)
  fileData.append('method', '1')
  fileData.append('description', '1')
  fileData.append('related_id', '1')
  fileData.append('user_id', userStore.userinfo.userId)
  uploadImg(fileData).then(result => {
    if (_data.uploadInfo && _data.uploadInfo.img_id) delUploadImg(_data.uploadInfo.img_id)
    _data.uploadInfo = result.data
  }, err => {})
};
const submit = () => {
  if (userStore.points < _deductionRules.value.flex) {
    emit('no-points')
    return
  }
  if (!imageUrl.value) {
    message.error('请上传需要扩展的图片')
    return
  }
  if (!imageUrl.value) return true
  _data.loading = true
  useImageExpend({
    conversation_id: !props.chatId || props.chatId === -1 || props.chatId === '-1' ? '' : props.chatId,
    description: '扩图',
    top: oForm.top,
    bottom: oForm.bottom,
    left: oForm.left,
    right: oForm.right,
    add_new_data: JSON.stringify({text: '扩图', type: 'extend',top: oForm.top,  bottom: oForm.bottom,left: oForm.left, right: oForm.right}),
    url: _data.uploadInfo.image_url
  }).then(res => {
    _data.uploadInfo.img_id = ''
    emit('change', {
      type: 'refine', sendInfo: {
        description: '扩图',
        top: oForm.top,
        bottom: oForm.bottom,
        left: oForm.left,
        right: oForm.right,
        add_new_data: JSON.stringify({text: '扩图', type: 'extend'}),
        url: _data.uploadInfo.image_url
      }, res: res.data
    }, res.data.conversation_id)
    //refreshResult(res.data.status_url)
  }).finally(() => {
    _data.timer2 = setTimeout(() => {
      _data.loading = false
    }, 15 * 1000)
  })
}
const init = (src) => {
  if (src) initUrl(src)
}
defineExpose({
  init
})
</script>

<style scoped lang="less">
.flex-col {
  height: 100%;

  .flex-1 {
    .tool-content {
      padding: 15px 10px;

      .operate-image {
        .image-view {
          width: 100%;
          height: 380px;
          background: @bg-page-color;
          border-radius: 8px;
          position: relative;

          &.up-box:hover, &.over {
            background: @bg-page-hover-color;
          }

          .up-btn {
            padding: 10px 5px;
            width: 100%;
            height: 380px;
            cursor: pointer;

            .ant-upload-file-tips {
              font-size: 12px;
            }
          }

          .close-img {
            font-size: 20px;
            position: absolute;
            top: -10px;
            right: -10px;
            color: #999999;
            z-index: 99;
            cursor: pointer;
          }

          .bg-wrap {
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
            background: #2F2F2F;
            width: 100%;

            .img-role-wrap {
              position: absolute;
              width: 100px;
              //border: 1px solid #ccc;
            }

            .img-role {
              //width: 100%;
              cursor: move;
            }

            .span-dot {
              width: 10px;
              height: 10px;
              position: absolute;
              border-color: #6a6a58;
              border-style: solid;
              z-index: 99;

              &.left {
                left: -3px;
                top: calc(50% - 5px);
                cursor: e-resize;
                border-left-width: 3px;
                border-right: none;
                border-bottom: none;
                border-top: none;
              }

              &.left-top {
                left: -3px;
                top: -3px;
                cursor: nw-resize;
                border-top-width: 3px;
                border-left-width: 3px;
                border-right: none;
                border-bottom: none;
              }

              &.top {
                top: -3px;
                left: calc(50% - 5px);
                cursor: n-resize;
                border-top-width: 3px;
                border-left: none;
                border-bottom: none;
                border-right: none;
              }

              &.right-top {
                right: -3px;
                top: -3px;
                cursor: ne-resize;
                border-top-width: 3px;
                border-right-width: 3px;
                border-left: none;
                border-bottom: none;
              }

              &.right {
                right: -3px;
                top: calc(50% - 5px);
                cursor: e-resize;
                border-right-width: 3px;
                border-left: none;
                border-bottom: none;
                border-top: none;
              }

              &.right-bottom {
                right: -3px;
                bottom: -3px;
                cursor: nw-resize;
                border-right-width: 3px;
                border-bottom-width: 3px;
                border-top: none;
                border-left: none;
              }

              &.bottom {
                bottom: -3px;
                left: calc(50% - 5px);
                cursor: n-resize;
                border-bottom-width: 3px;
                border-left: none;
                border-top: none;
                border-right: none;
              }

              &.left-bottom {
                left: -3px;
                bottom: -3px;
                cursor: ne-resize;
                border-left-width: 3px;
                border-bottom-width: 3px;
                border-right: none;
                border-top: none;
              }

            }
          }

          .drag_box {
            position: absolute;
            top: 0;
            left: 0;
            border: 1px solid #FFFFFF;
          }
        }
      }
    }

    .collapse-box {
      margin-top: 15px;
      padding: 0 10px;

      .collapse-content-title {
        margin: 10px 0;
        font-size: 14px;
        padding: 5px;
        border-radius: 8px;
        background-color: #2F2F2F;
        color: #9C9C9C;

        .tab-item {
          cursor: pointer;
          line-height: 40px;
          text-align: center;
          border-radius: 8px;

          &.active {
            background-color: #181818;
            color: #FFFFFF;
          }
        }
      }

      .fixed-item {
        display: inline-block;
        width: calc(25% - 6px);
        height: 70px;
        margin-right: 8px;
        border-radius: 8px;
        color: #999999;
        background-color: #2F2F2F;
        cursor: pointer;

        > .fixed-box {
          height: 100%;
          width: 100%;
        }

        .iconfont {
          color: #999999;
          font-size: 20px;
        }

        &:nth-child(4n) {
          margin-right: 0;
        }

        &.active {
          background-color: #181818;
          color: #FFFFFF;

          .iconfont {
            color: #FFFFFF;
          }
        }
      }

      .customize {
        .item-input {
          width: 120px;
          margin: 5px 10px;

          .ipt {
            border-color: #333333;

            :deep(.ant-input-suffix) {
              font-size: 12px;
            }
          }
        }
      }
    }
  }

  .bottom-btn {
    margin: 30px 10px;
    height: 40px;
    //border-radius: 20px;
    //display: flex;
    //align-items: center;
    //justify-content: center;
    //color: #fff;
    //cursor: pointer;
    //background: linear-gradient(to right, #AC4FFE, #5A50FE 50%, #AC4FFE);
    //font-size: 16px;
    //
    //.iconfont {
    //  font-size: 16px;
    //  margin-right: 5px;
    //}
    //
    //&:hover {
    //  opacity: 0.8;
    //}
    .send-btn {
      width: 100%;
      display: flex;
      font-size: 14px;
      cursor: pointer;
      color: #fff;
      border: 0;
      background: @btn-bg-color;

      .iconfont {
        fill: #FFFFFF;
        font-size: 14px;
        margin-right: 5px
      }

      &[disabled] {
        cursor: not-allowed !important;
      }

      &:hover {
        opacity: 0.8;
      }
    }
  }
}
</style>
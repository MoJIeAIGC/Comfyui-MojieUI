<template>
  <div class="flex flex-col">
    <div class="flex-1 h-0-o-a">
      <div class="tool-content">
        <div class="flex operate-image">
          <div class="flex-1">
            <div class="title"><span class="required">*</span>产品原图</div>
            <div>
              <ImageView ref="imageViewProRef" type="pro" @change="imageChange"/>
            </div>
          </div>
          <div class="flex-1">
            <div class="title"><span class="required">*</span>迁移场景(被迁移图片)</div>
            <div>
              <ImageView ref="imageViewReplaceRef" type="replace" @change="imageChange"/>
            </div>
          </div>
        </div>
      </div>
      <div class="tip-box">
        请保持替换主体在正中间，会自动抠图处理
      </div>
      <div class="help-box flex items-start">
        <div class="show-help flex items-center justify-center" @click="showHelp"><i
            class="iconfont icon-a-ziyuan31"></i> 点击查看视频教程
          <right-outlined class="icon-right"/>
        </div>
      </div>
      <!--      <div class="tool-content">-->
      <!--        <div class="flex operate-image">-->
      <!--          <div class="flex-1">-->
      <!--            <img :src="_data.aaabase.pro" style="width: 100%" />-->
      <!--          </div>-->
      <!--          <div class="flex-1">-->
      <!--            <img :src="_data.aaabase.replace" style="width: 100%"/>-->
      <!--          </div>-->
      <!--        </div>-->
      <!--      </div>-->
      <div class="collapse-box">
        <a-collapse v-model:activeKey="activeKey" :bordered="false" expand-icon-position="right">
          <template #expandIcon="{ isActive }">
            <a-switch size="small" :checked="!!isActive"/>
          </template>
          <a-collapse-panel key="1" header="高级设置" :style="customStyle">
            <div>
              <div class="flex collapse-content-title justify-start items-center">
                <div>全图提示词</div>
              </div>
              <div>
                <a-textarea class="ipt-area" v-model:value="_data.generate.text" placeholder="可以简单描述一下画面" :rows="4"/>
<!--                <a-textarea class="ipt-area" v-model:value="_data.generate.text"-->
<!--                            @change="textChange('text')"-->
<!--                            placeholder="可以简单描述一下画面" :rows="4"/>-->
              </div>
              <div class="flex collapse-content-title justify-start items-center">
                <div>还原强度</div>
              </div>
              <div class="flex generate">
                <div class="flex-1">
                  <a-slider :min="0.1" :max="0.9" :precision="1" :step="0.1" v-model:value="_data.generate.strength"/>
                </div>
                <div>
                  <a-input-number
                      class="ipt-num"
                      v-model:value="_data.generate.strength"
                      :min="0.1"
                      :max="0.9"
                      :step="0.1"
                      style="margin-left: 16px"
                  />
                </div>
              </div>
            </div>
          </a-collapse-panel>
        </a-collapse>
      </div>
    </div>
    <div class="bottom-btn">
      <a-button type="primary" size="large" shape="round" class="send-btn items-center justify-center"
                :disabled="isDis" @click="submit" :loading="_data.loading">
        <template #icon>
          <i class="iconfont icon-a-ziyuan19"></i>
        </template>
        立即生成（{{ pointText }}）
      </a-button>
    </div>
  </div>
</template>
<script setup>

import ImageView from "@/components/imageEdit/imageView.vue";
import {reactive, ref, onUnmounted, defineProps, defineEmits, computed, defineExpose} from "vue";
import {base64UrlToFile} from "@/utils/utils.js";
import {uploadImg, delUploadImg} from "@/api/upload.js";
import {getTranslateToEn, getWhiteImageFile, replaceProductImage} from "@/api/product.js";
import {useUserStore} from "@/store/userStore.js";
import {message} from "ant-design-vue";
import {deductionRules} from "@/options/model.js";
import emitter from "@/utils/emitter.js";
import {RightOutlined} from "@ant-design/icons-vue";

const emit = defineEmits(['change', 'no-points']);
const userStore = useUserStore()
const imageViewProRef = ref()
const imageViewReplaceRef = ref()
const _data = reactive({
  timer2: null,
  loading: false,
  maskDraw: false,
  proUpdating: false,
  isUpdating: false,
  aaabase: {
    pro: "",
    replace: "",
  },
  pro: {},
  replace: {},
  maskImage: {},
  whiteImage: {},
  strengthList: [
    {type: '0.6', name: '低'},
    {type: '0.8', name: '中'},
    {type: '1.0', name: '高'},
  ],
  quantityList: [
    {type: '1', isVip: false},
    {type: '2', isVip: true},
    // {type: '3', isVip: true},
    // {type: '4', isVip: true}
  ],
  generate: {
    templateText: '',
    text: '',
    quantity: '1',
    strength: 0.8
  },
  generateEn: {
    templateText: '',
    text: ''
  },
  timer: null
})
onUnmounted(() => {
  if (_data.timer2) clearTimeout(_data.timer2);
  if (_data.timer) clearTimeout(_data.timer);
})
const isDis = computed(() => {
  if (_data.loading) return _data.loading
  return false
});
const _deductionRules = computed(() => {
  const isVip = userStore.vipInfo && userStore.vipInfo.level
  return isVip ? deductionRules.vip : deductionRules.default
});
const pointText = computed(() => {
  const isVip = userStore.vipInfo && userStore.vipInfo.level
  if (_deductionRules.value.ai_product === 0 && isVip) return '会员免费'
  return '消耗' + _deductionRules.value.ai_product + '算力'
});
const activeKey = ref([]);
const customStyle = 'background: rgb(25, 25, 27);border-radius: 4px;border: 0;overflow: hidden';
const quantityChange = (item) => {
  if (item.isVip) return
  _data.generate.quantity = item.type
}
const showHelp = () => {
  emitter.emit('video-tutorial', '迁移替换') //产品替换鼠标移动全局监听
}
const imageChange = async (base64, type, maskUrl, isDraw, aaabase) => {
  // if (aaabase) {
  //   _data.aaabase[type] = aaabase
  // }
  if (base64 === 'clear') {
    if (type === 'pro') {
      if (_data.pro.img_id) delUploadImg(_data.pro.img_id)
      if (_data.whiteImage.image_id) delUploadImg(_data.whiteImage.image_id)
      _data.pro = {}
      _data.whiteImage = {}
    }
    if (type === 'replace') {
      if (_data.replace.img_id) delUploadImg(_data.replace.img_id)
      if (_data.maskImage.img_id) delUploadImg(_data.maskImage.img_id)
      _data.replace = {}
      _data.maskImage = {}
    }
    return
  }
  const file = base64UrlToFile(base64)
  if (type === 'pro') {
    _data.proUpdating = true
    _data.pro = {}
    _data.whiteImage = {}
    try {
      await uploadImage(file, type)
      await refreshWhiteImageFile(file)
      _data.proUpdating = false
    } catch (e) {
      _data.proUpdating = false
    }
  }
  if (type === 'replace') {
    _data.maskDraw = isDraw
    if (maskUrl) {
      _data.replace = {}
      _data.maskImage = {}
      _data.isUpdating = true
      try {
        await uploadImage(file, type)
        const maskFile = base64UrlToFile(maskUrl)
        await uploadImage(maskFile, 'maskImage')
        _data.isUpdating = false
      } catch (e) {
        _data.isUpdating = false
      }
    } else {
      _data.replace = {image_url: 'loading'}
    }
  }
}
const props = defineProps({
  chatId: {
    type: [String, Number],
    default: ''
  }
})
// const textChange = (type) => {
//   if (_data.timer) clearTimeout(_data.timer)
//   if(_data.generate[type]){
//     _data.timer = setTimeout(async ()=>{
//       let _res = await getTranslateToEn(_data.generate[type])
//       if(_res.data&&_res.data.translated_text)  _data.generateEn[type] = _res.data.translated_text
//     },0.7*1000)
//   } else {
//     _data.generateEn[type] = ''
//   }
// }
const uploadImage = async (file, type) => {
  return new Promise((resolve, reject) => {
    if (_data[type].img_id) delUploadImg(_data[type].img_id)
    _data[type].img_id = {}
    const fileData = new FormData();
    fileData.append('image', file)
    fileData.append('method', '1')
    fileData.append('description', '1')
    fileData.append('related_id', '1')
    fileData.append('user_id', userStore.userinfo.userId)
    uploadImg(fileData).then(result => {
      _data[type] = result.data
    }).finally(() => {
      resolve()
    })
  })
};
const refreshWhiteImageFile = async (file) => {
  return new Promise((resolve, reject) => {
    if (_data.whiteImage.image_id) delUploadImg(_data.whiteImage.image_id)
    _data.whiteImage = {}
    const fileData = new FormData();
    fileData.append('image', file)
    fileData.append('description', 'Obtain a white background image')
    getWhiteImageFile(fileData).then(result => {
      _data.whiteImage = result.data
    }).finally(() => {
      resolve()
    })
  })
};
const submit = async () => {
  if (userStore.points < _deductionRules.value.ai_product) {
    emit('no-points')
    return
  }

  if (!_data.proUpdating && !_data.whiteImage.image_url) {
    message.error('请在左边上传产品图')
    _data.loading = false
    return
  }
  if (!_data.isUpdating) {
    if (!_data.replace.image_url) {
      message.error('请在右边上传替换的场景图')
      _data.loading = false
      return
    }
    if (!_data.maskDraw || !_data.maskImage.image_url) {
      message.error('请对替换图片需要替换的区域进行涂抹')
      _data.loading = false
      return
    }
  }
  _data.loading = true

  if (_data.isUpdating === true || _data.proUpdating === true) {
    if (_data.timer) clearTimeout(_data.timer)
    _data.timer = setTimeout(() => {
      submit()
    }, 1000)
    return
  }
  if (_data.generate['text']) {
    let _res = await getTranslateToEn(_data.generate['text'])
    if (_res.data && _res.data.translated_text) _data.generateEn['text'] = _res.data.translated_text
  }
  let text = 'This is a collage picture，in the left Objects replaces the Objects in the right picture,'
  if (_data.generate.templateText) {
    text = `the left image is ${_data.generateEn.templateText},`
  }
  if (_data.generate.text) text = text + _data.generateEn.text
  replaceProductImage({
    conversation_id: !props.chatId || props.chatId === -1 || props.chatId === '-1' ? '' : props.chatId,
    //description: 'the left image is a subject,the subject on the right image',

    add_new_data: JSON.stringify({
      text: _data.generate.text,
      templateText: _data.generate.templateText,
      url: _data.pro.image_url,
      type: 'product_replacement'
    }),
    description: text,
    level: _data.generate.strength,
    white_url: _data.whiteImage.image_url,
    template_url: _data.replace.image_url,
    mask_url: _data.maskImage.image_url
  }).then(res => {
    _data.whiteImage.image_id = ''
    _data.replace.img_id = ''
    _data.maskImage.img_id = ''
    _data.pro.img_id = ''
    emit('change', {sendInfo: 'replace', res: res.data}, res.data.conversation_id)
    // refreshResult(res.data.status_url)
  }).finally(() => {
    _data.timer2 = setTimeout(() => {
      _data.loading = false
    }, 15 * 1000)
  })
}
const init = (src) => {
  if (src) imageViewReplaceRef.value.initSrc(src)
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
      padding: 15px 10px 5px;

      .operate-image {
        .title {
          margin-bottom: 10px;
        }

        .flex-1 {
          margin: 5px;
        }

        .required {
          color: #ff4d4f;
        }
      }
    }

    .tip-box {
      padding: 0 12px;
      font-size: 12px;
    }

    .help-box {
      padding: 10px 12px 5px;

      .show-help {
        background: #405FFF;
        cursor: pointer;
        font-size: 12px;
        line-height: 30px;
        border-radius: 4px;
        padding: 0 15px;

        .iconfont {
          font-size: 14px;
          line-height: 14px;
          margin-right: 5px;
          margin-top: 1px;
        }

        .icon-right {
          margin-top: 2px;
          margin-left: 5px;
        }

        //font-size: 12px;
      }
    }

    .collapse-box {
      .collapse-content-title {
        font-size: 14px;
        padding: 15px 0;
        color: #FFFFFF;
      }

      .ipt {
        border-radius: 8px;
        height: 40px;
        background-color: @bg-page-color;
        border: 0;
        color: #ffffff;
        font-size: 14px;

        &::placeholder {
          font-size: 12px;
        }
      }

      .ipt-area {
        border-radius: 8px;
        background-color: @bg-page-color;
        border: 0;
        color: #ffffff;
        font-size: 14px;

        &::placeholder {
          font-size: 12px;
        }
      }

      .strength-item {
        line-height: 40px;
        background: @bg-page-color;
        cursor: pointer;
        border-radius: 8px;

        &:nth-child(n+2) {
          margin-left: 10px;
        }

        &.active {
          background: #2D6CF5;
        }
      }

      .generate {
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

        :deep(.ant-slider-dot-active) {
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

        .ipt-num {
          border-radius: 8px;
          border-color: #2D6CF5;
        }

        :deep(.ant-input-number-handler) {
          border-color: #2D6CF5;
        }
      }

      .quantity-item {
        position: relative;
        line-height: 40px;
        background: @bg-page-color;
        cursor: pointer;
        border-radius: 8px;
        width: 40px;

        .iconfont {
          font-size: 14px;
          color: #F5C870;
          position: absolute;
          top: 0;
          right: 0;
          line-height: 14px;
        }

        &:nth-child(n+2) {
          margin-left: 10px;
        }

        &.active {
          background: #2D6CF5;
        }

        &.disabled {
          cursor: not-allowed;
          background: #999999;
        }
      }
    }
  }

  .bottom-btn {
    //position: absolute;
    //left: 10px;
    //width: calc(100% - 20px);
    //bottom: 30px;
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
    //&.disabled {
    //  cursor: not-allowed;
    //}
    //
    //&:hover {
    //  opacity: 0.8;
    //}
    //
    //.iconfont {
    //  font-size: 16px;
    //  margin-right: 5px;
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

<template>
  <div class="flex flex-col">
    <div class="flex-1 h-0-o-a">
      <div class="tool-content">
        <div class="operate-image">
          <fabricView ref="fabricViewRef" type="refine"  @change="fileProcessing"/>
        </div>
      </div>
<!--      <div class="tool-content">-->
<!--        <div class="flex operate-image">-->
<!--          <div class="flex-1">-->
<!--            <div>-->
<!--              <img style="width: 100%"  :src="_data.image.image_url"/>-->
<!--            </div>-->
<!--          </div>-->
<!--          <div class="flex-1">-->
<!--            <div>-->
<!--              <img  style="width: 100%"  :src="_data.maskImage.image_url"/>-->
<!--            </div>-->
<!--          </div>-->
<!--        </div>-->
<!--      </div>-->
      <div class="collapse-box">
        <div>
          <div class="flex collapse-content-title justify-start items-center">
            <div>调整提示词</div>
          </div>
          <div>
            <a-textarea class="ipt-area" @change="textChange" v-model:value="_data.text" placeholder="可以这样描述：" :rows="4" />
          </div>
        </div>
        <div class="flex collapse-content-title justify-start items-center">
          <div>精修强度</div>
        </div>
        <div class="strength">
          <div class="flex">
            <div class="flex-1">
              <a-slider :min="0.1" :max="0.9" :step="0.1" v-model:value="_data.strength" />
            </div>
            <div>
              <a-input-number
                  class="ipt-num"
                  v-model:value="_data.strength"
                  :min="0.1"
                  :max="0.9"
                  :precision="1"
                  :step="0.1"
                  style="margin-left: 16px"
              />
            </div>
<!--            <div v-for="item in _data.strengthList" :key="item.type" class="flex-1 text-center strength-item"-->
<!--                 :class="{active:item.type === _data.strength}"-->
<!--                 @click="_data.strength=item.type">-->
<!--              {{item.name}}-->
<!--            </div>-->
          </div>
        </div>
      </div>
    </div>
    <div class="bottom-btn">
      <a-button type="primary" size="large"  shape="round" class="send-btn items-center justify-center" @click="getFileInfo" :loading="_data.loading">
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

import fabricView from "@/components/imageEdit/fabricView.vue";
import {computed, defineEmits, defineExpose, defineProps, onUnmounted, reactive, ref} from "vue";
import {base64UrlToFile} from "@/utils/utils.js";
import {uploadImg} from "@/api/upload.js";
import {getTranslateToEn, useImageDetailRefinement} from "@/api/product.js";
import {useUserStore} from "@/store/userStore.js";
import {message} from "ant-design-vue";
import {deductionRules} from "@/options/model.js";
const emit = defineEmits(['change','no-points']);
const userStore = useUserStore()
const fabricViewRef = ref()
const _data = reactive({
  loading:false,
  strengthList: [
    {type: '0.2', name: '低'},
    {type: '0.4', name: '中'},
    {type: '0.6', name: '高'},
  ],
  text: '',
  textEn: '',
  strength: 0.4,
  timer: null,
  timer2: null,
  image: {},
  maskImage: {},
  isDraw:false
})
onUnmounted(() => {
  if( _data.timer2) clearTimeout(_data.timer2);
  if( _data.timer) clearTimeout(_data.timer);
})
const _deductionRules = computed(() => {
  const isVip = userStore.vipInfo&&userStore.vipInfo.level
  return  isVip ? deductionRules.vip : deductionRules.default
});
const pointText = computed(() => {
  const isVip = userStore.vipInfo&&userStore.vipInfo.level
  if(_deductionRules.value.flex === 0 &&isVip)  return '会员免费'
  return  '消耗'+_deductionRules.value.flex +'算力'
});
const fileProcessing = async (startBase64,imgBase64,mBase64,isDraw) => {
  const imgFile = base64UrlToFile(startBase64)
  const maskFile = base64UrlToFile(mBase64)
  _data.isDraw = isDraw
  if(!isDraw){
    message.error(`请对图片需要调整的区域进行涂抹`)
    return
  }
   _data.image = {}
  _data.maskImage = {}
  _data.loading= true
  try {
    await uploadImage(imgFile,'start')
    await uploadImage(maskFile,'mask')
    submit()
  } catch (error) {
    _data.loading= false
  }
}
const textChange = () => {
  // if (_data.timer) clearTimeout(_data.timer)
  // if(_data.text){
  //   _data.timer = setTimeout(async ()=>{
  //     let _res = await getTranslateToEn(_data.text)
  //     if(_res.data&&_res.data.translated_text)  _data.textEn = _res.data.translated_text
  //   },0.7*1000)
  // } else {
  //   _data.textEn = ''
  // }
}
const props = defineProps({
  src: {
    type:String,
    default:''
  },
  chatId: {
    type:[String,Number],
    default:''
  }
})
const uploadImage = async (file, type) => {
  return new Promise((resolve, reject) => {
    const fileData = new FormData();
    fileData.append('image', file)
    fileData.append('method', '1')
    fileData.append('description', '1')
    fileData.append('related_id', '1')
    fileData.append('user_id', userStore.userinfo.userId)
    uploadImg(fileData).then(result => {
      if(type === 'start') _data.image = result.data
      if(type === 'mask') _data.maskImage = result.data
      resolve(result)
    }, err => {
      resolve(err)
    })
  })
};
const getFileInfo = () => {
  if(userStore.points<_deductionRules.value.flex) {
    emit('no-points')
    return
  }
  fabricViewRef.value.handleOk('mask')
}
const submit = async () => {
  _data.textEn = ''
  if(_data.text){
    let _res = await getTranslateToEn(_data.text)
    if(_res.data&&_res.data.translated_text)  _data.textEn = _res.data.translated_text
  }
  useImageDetailRefinement({
    conversation_id: !props.chatId || props.chatId===-1||props.chatId==='-1'?'':props.chatId,
    description: _data.textEn|| _data.text  || 'refine',
    add_new_data:JSON.stringify({ text:_data.text || '精修' ,type:'refine'}),
    level: _data.strength,
    url: _data.image.image_url,
    mask_url: _data.maskImage.image_url
  }).then(res=>{
    emit('change', {type:'refine', sendInfo: {
        description: _data.text,
        level: _data.strength,
        url: _data.image.image_url,
        mask_url: _data.maskImage.image_url
      },res:res.data},res.data.conversation_id)
  }).finally(res=>{
   _data.timer2 = setTimeout(()=>{
      _data.loading= false
    },15000)
  })
}
const init = (src) =>{
  if(src) fabricViewRef.value.setInit(src)
}
defineExpose({
  init
})
</script>

<style scoped lang="less">
.flex-col{
  height: 100%;
  .flex-1{
    .tool-content {
      padding: 15px 10px;
      .operate-image {

      }
    }
    .collapse-box {
      margin-top: 15px;
      padding: 0 10px;
      .collapse-content-title {
        font-size: 14px;
        padding: 15px 0;
        color: #FFFFFF;
      }
      .ipt-area {
        border-radius: 8px;
        background-color:@bg-page-color;
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
    }
  }
  .strength{
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
    :deep(.ant-slider-dot-active){
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
    .ipt-num{
      border-radius: 8px;
      border-color: #2D6CF5;
    }
    :deep(.ant-input-number-handler) {
      border-color: #2D6CF5;
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
    .send-btn {
      width:100%;
      display: flex;
      font-size: 14px;
      cursor: pointer;
      color: #fff;
      border: 0;
      background: @btn-bg-color;
      .iconfont{
        fill: #FFFFFF;
        font-size: 14px;
        margin-right: 5px
      }
      &[disabled]{
        cursor: not-allowed!important;
      }
      &:hover {
        opacity: 0.8;
      }
    }
    //.iconfont{
    //  font-size: 16px;
    //  margin-right: 5px;
    //}
    //&:hover {
    //  opacity: 0.8;
    //}

  }
}
</style>
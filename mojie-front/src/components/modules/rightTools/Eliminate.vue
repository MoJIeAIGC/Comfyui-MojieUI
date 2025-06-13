<template>
  <div class="flex flex-col">
    <div class="flex-1 h-0-o-a">
      <div class="tool-content">
        <div class="operate-image">
          <fabricView ref="fabricViewRef" type="eliminate" @change="fileProcessing"/>
        </div>
      </div>
<!--            <div class="tool-content">-->
<!--              <div class="flex operate-image">-->
<!--                <div class="flex-1">-->
<!--                  <div>-->
<!--                    <img style="width: 100%"  :src="_data.image.image_url"/>-->
<!--                  </div>-->
<!--                </div>-->
<!--                <div class="flex-1">-->
<!--                  <div>-->
<!--                    <img  style="width: 100%"  :src="_data.maskImage.image_url"/>-->
<!--                  </div>-->
<!--                </div>-->
<!--              </div>-->
<!--            </div>-->
      <div class="collapse-box">
        <div>
          <div class="flex collapse-content-title">
            <div class="tab-item flex-1" :class="{active: tabIndex === '1'}" @click="tabIndex='1'">内补功能</div>
            <div class="tab-item flex-1" :class="{active: tabIndex === '2'}" @click="tabIndex='2'">消除功能</div>
          </div>
          <div>
            <a-textarea class="ipt-area" v-if="tabIndex==='1'" v-model:value="_data.text"
                        placeholder="可以这样描述：补充xxx" :rows="4"/>
<!--            <a-textarea class="ipt-area" v-if="tabIndex==='1'" @change="textChange('text')" v-model:value="_data.text"-->
<!--                        placeholder="可以这样描述：补充xxx" :rows="4"/>-->
<!--            <a-textarea class="ipt-area" v-if="tabIndex==='2'"  @change="textChange('eliminate')"   v-model:value="_data.eliminate"-->
<!--                        placeholder="可以这样描述：去掉xxx" :rows="4"/>-->
          </div>
        </div>
      </div>
    </div>
    <div class="bottom-btn">
      <a-button type="primary" size="large" shape="round" class="send-btn items-center justify-center" :disabled="_data.loading" @click="getFileInfo" :loading="_data.loading">
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
import {uploadImg} from "@/api/upload.js";
import {computed, defineEmits, defineExpose, defineProps, onUnmounted, reactive, ref} from "vue";
import {base64UrlToFile} from "@/utils/utils.js";
import {useUserStore} from "@/store/userStore.js";
import {getTranslateToEn, imageInternal, imageInternalRemoval} from "@/api/product.js";
import {message} from "ant-design-vue";
import {deductionRules} from "@/options/model.js";
const emit = defineEmits(['change','no-points']);
const userStore = useUserStore()
const fabricViewRef = ref()
const props = defineProps({
  chatId: {
    type:[String,Number],
    default:''
  }
})
const _data = reactive({
  loading:false,
  text: '',
  eliminate: '',
  textEn: '',
  eliminateEn: '',
  image: {},
  maskImage:  {},
  isDraw:false,
  timer2: null,
  timer:null
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
// const textChange = (type) => {
//   // if (_data.timer) clearTimeout(_data.timer)
//   // if(_data[type]){
//   //   _data.timer = setTimeout(async ()=>{
//   //     let _res = await getTranslateToEn(_data.text)
//   //     if(_res.data&&_res.data.translated_text) _data.textEn = _res.data.translated_text
//   //   },0.7*1000)
//   // } else {
//   //   _data[type+'En'] = ''
//   // }
// }
onUnmounted(() => {
  if( _data.timer2) clearTimeout(_data.timer2);
  if( _data.timer) clearTimeout(_data.timer);
})
const tabIndex = ref('1')
const fileProcessing = async (startBase64,imgBase64,mBase64,isDraw) => {
  const imgFile = base64UrlToFile(startBase64)
  const maskFile = base64UrlToFile(mBase64)
  //_data.isDraw = isDraw
  if(!isDraw){
    let t = tabIndex.value==='1'? '替换':'消除'
    message.error(`请对图片需要${t}的区域进行涂抹`)
    return
  }
  _data.loading= true
  try {
    await uploadImage(imgFile,'start')
    await uploadImage(maskFile,'mask')
    submit()
  } catch (e) {
    _data.loading= false
  }
}
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
      resolve()
    }, err => {
      resolve()
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
  if(_data.text&&tabIndex.value==='1'){
    let _res = await getTranslateToEn(_data.text)
    if(_res.data&&_res.data.translated_text) _data.textEn = _res.data.translated_text
  }
  const sub_data = {
    conversation_id: !props.chatId || props.chatId===-1||props.chatId==='-1'?'':props.chatId,
    description:tabIndex.value==='1'?(_data.textEn|| _data.text): 'Remove here',
    add_new_data:JSON.stringify({
      text:tabIndex.value==='1'?_data.text: _data.eliminate,
      type:'eliminate',
    }),
    url: _data.image.image_url,
    mask_url: _data.maskImage.image_url
  }
  if(tabIndex.value==='1') {
    imageInternal(sub_data).then((res) => {
      emit('change', {type:'eliminate', sendInfo: {
          description: "string",
          url: _data.image.image_url,
          mask_url: _data.maskImage.image_url
        },res: res.data},res.data.conversation_id)
    }).finally(()=>{
      _data.timer2 = setTimeout(()=>{
        _data.loading= false
      },15 * 1000)
    })
  }
  if(tabIndex.value==='2') {
    imageInternalRemoval(sub_data).then((res) => {
      emit('change', {type:'eliminate', sendInfo: {
          description: "string",
          url: _data.image.image_url,
          mask_url: _data.maskImage.image_url
        },res: res.data},res.data.conversation_id)
    }).finally(()=>{
      _data.timer2 = setTimeout(()=>{
        _data.loading= false
      },15 * 1000)
    })
  }
}
const init = (src) =>{
  if(src) fabricViewRef.value.setInit(src)
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
        .tab-item{
          cursor: pointer;
           line-height: 40px;
          text-align: center;
          border-radius: 8px;
          &.active{
            background-color: @bg-page-color;
            color: #FFFFFF;
          }
        }
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
        background:@bg-page-color;
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

  }
}
</style>
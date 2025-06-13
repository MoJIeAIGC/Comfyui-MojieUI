<template>
  <a-modal class="user-modal" v-model:visible="_data.visible" destroyOnClose :maskClosable="false" :width="modalWidth" :footer="null">
    <div slot="title"></div>
    <a-spin :spinning="_data.loading">
    <div class="member-content">
      <div class="cell-item flex">
        <div class="flex flex-1 justify-center items-center left-image-box">
          <div class="image-box">
            <img v-if="imageInfo.image_path_res" :style="imageStyle" :src="getChildList(imageInfo.image_path_res)" alt=""/>
          </div>
        </div>
        <div class='example-info'>
          <div ref="exampleRef">
            <div class="title">使用模型</div>
            <div class="modal-name flex items-center">
              <i class="iconfont flex" :class="modelInfo.icon"></i>
              <div class="text-box flex-1">
                <div class="t1">{{ modelInfo.label }}</div>
                <div class="t2">{{ modelInfo.tip }}</div>
              </div>
            </div>
            <div class="title" v-if="imageInfo.image_path">辅助图片</div>
            <div class="auxiliary-image" v-if="imageInfo.image_path">
              <div class="auxiliary-image-item" v-for="(item,index) in list">
                <div class="">
                  <img :src="item.url" v-db-click-img :data-index="index" @load="imageLoad" alt="">
                </div>
              </div>
            </div>
            <div class="title" v-if="imageInfo.text">提示词</div>
            <div class="auxiliary-text text" v-if="imageInfo.text">
              {{ imageInfo.text }}
            </div>
            <div class="title">图片参数</div>
            <div class="image-table">
              <div class="flex">
                <div class="flex-1">图像尺寸</div>
                <div class="flex-1"> {{ imageInfo.width }}*{{ imageInfo.height }}</div>
              </div>
              <div class="flex">
                <div class="flex-1">图像格式</div>
                <div class="flex-1"> {{ imageInfo.imageType }}</div>
              </div>
            </div>
            <div class="like flex items-center">
              <div class="flex justify-center items-center" @click="downLoadImage(imageInfo.image_path_res)"  title="下载">
                <i class="iconfont icon-xiazai1"></i>
              </div>
              <div class="flex justify-center items-center" title="分享" @click="copyLink(imageInfo.image_path_res)">
                <i class="iconfont icon-fenxiang1"></i>
              </div>
              <div class="flex justify-center items-center like-box" @click="doLike" :class="{active:imageInfo.is_liked ===1}"  title="喜欢">
                <i class="iconfont icon-_like"></i>
                {{imageInfo.like_count}}
              </div>
            </div>
<!--            <div class="footer-btn" v-if="props.isChat">-->
            <div class="footer-btn">
              <a-button class="btn" type="primary"
                        :disabled="_data.btnLoading"
                        @click="doSend">
                生成同款({{pointsText}})
              </a-button>
            </div>
          </div>
        </div>
      </div>
    </div>
    </a-spin>
  </a-modal>
</template>

<script setup>
import {computed, defineEmits, defineProps, nextTick, reactive, ref} from 'vue'
import { gcd,getModelByKey} from "@/utils/utils.js";
import {message, Modal} from "ant-design-vue";
import {getTranslateToEn} from "@/api/product.js";
import {queryTempGood} from "@/api/example.js";
import {newConver, postChatGPT, postCombined, postFluxKonTextCombined, postGemini, postVolcengine} from "@/api/chat.js";
import {deductionRules} from "@/options/model.js";
import {useUserStore} from "@/store/userStore.js";
import {useRouter} from "vue-router";
import emitter from "@/utils/emitter.js";
const userStore = useUserStore();
const router = new useRouter();
const props = defineProps({
  isChat: {
    type: Boolean,
    default: false
  }
})
const _deductionRules = computed(() => {
  const isVip = userStore.vipInfo&&userStore.vipInfo.level
  return  isVip ? deductionRules.vip : deductionRules.default
});
const isLogin = computed(() => {
   if(userStore.token){
     let isExpire = 1
     if(userStore.dataTime) isExpire =  new Date().getTime() - userStore.dataTime - 23 * 60 * 60 * 1000 - 55*60*1000;
     return isExpire <= 0;
   }
   return false
});
const sendPoints = computed(() => {
  const _Rules = _deductionRules.value
  let _modelType = modelInfo.value.value
  let points = _modelType === 'gpt-4o-image' ? _Rules['gpt-4o-image'] : _Rules['flex']
  if (_modelType === 'flex'&&list.value.length > 0) points =  _Rules['flux_kontext_pro_2']
  if (_modelType === 'qiHua') {
    if(list.value.length > 0) {
      points =_Rules['flux_kontext_pro_1']
    } else {
      points = _Rules['qiHua']
    }
  }
  return points
});
const pointsText = computed(() => {
  const isVip = userStore.vipInfo&&userStore.vipInfo.level
  if (isVip &&sendPoints.value ===0) return '会员免费'
  return  '消耗'+sendPoints.value +'算力'
});
const emit = defineEmits(['change', 'refresh']);
const list = ref([])
const imageInfo = ref({})
const modelInfo = ref({})
const exampleRef = ref()
const imageStyle = ref({})
const modalWidth = ref('800px')
const _data = reactive({
  loading:false,
  btnLoading:false,
  visible: false
})
const getChildList = (urls) => {
  if (!urls) return ''
  let url =  urls.split(',')[0]
  imageInfo.value.imageType = url.split('.')[url.split('.').length - 1]
  return url
}
const downLoadImage = (urls) => {
  if (!urls) {
    message.error('未找到图片链接')
    return
  }
  window.open(urls.split(',')[0], '_blank')
}
const getImageList = (urls) => {
  let _list = []
  if (urls) _list = urls.split(',')
  list.value = []
  for (let _url of _list) {
    list.value.push({
      width: 0,
      height: 0,
      url: _url,
      load: false,
      type: _url.split('.')[_url.split('.').length - 1]
    })
  }
}
const doLike = () => {
  // waterfallRef.value.resize()
  queryTempGood({example_id: imageInfo.value.id}).then(res => {
    if (res.code !== 200) return
    if (imageInfo.value.is_liked === 1) {
      imageInfo.value.is_liked = 0
      imageInfo.value.like_count -= 1
    } else {
      imageInfo.value.is_liked = 1
      imageInfo.value.like_count += 1
    }
    emit('refresh', imageInfo.value, imageInfo.value.index)
  })
}
const copyLink = (urls) => {
  if (!urls) {
    message.error('未找到图片链接')
    return
  }
  try {
    const textarea = document.createElement("textarea");
    textarea.value = urls.split(',')[0];
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
    message.success('复制链接成功')
  } catch (error) {
    message.error('复制链接失败')
  }
}
const imageLoad = (event) => {
  console.log('imageLoad', event)
  // const imgEl = event.target
  // const index = imgEl.getAttribute('data-index')
  // list.value[index].width = imgEl.naturalWidth
  // list.value[index].height = imgEl.naturalHeight
  // list.value[index].load = true
}
const doSend = async () => {
  if(!isLogin.value) { //未登录或token过期
    userStore.setShowLogin(true);
    return
  }
  _data.btnLoading=true
  const _list = list.value.map((item) => {
    return item.url
  })
  let obj = {}
  let _obj2 = {
    width: imageInfo.value.width,
    height: imageInfo.value.height,
    quantity: 1,
    image_urls: _list,
    text: imageInfo.value.text, //图像生成描述文本
  }
  if (modelInfo.value.value === 'flex') {
    obj = {
      description: imageInfo.value.text,
      ..._obj2,
      add_new_data: JSON.stringify({
        text: imageInfo.value.text
      }),
    }
    try {
      if(_list.length===0){
        let _resEn = await getTranslateToEn(imageInfo.value.text)
        if (_resEn.data && _resEn.data.translated_text) obj.description = _resEn.data.translated_text
      }
    } catch (err) {
      console.log(err)
    }
  }
  if (modelInfo.value.value === 'qiHua') {
    obj = {
      "stream": false,
      ..._obj2,
    }
  }
  if (modelInfo.value.value === 'gpt-4o-image') {
     let _a =  imageInfo.value.width  /  imageInfo.value.height
    obj = {
      "model": 'gpt-4o-image',
      image_paths: _list,
      "stream": false,
      operation_type: _list.length>0 ?'edit':'generate',
      "prompt": imageInfo.value.text, //图像生成描述文本
      "text": imageInfo.value.text, //图像生成描述文本
      size:_a === 1? '1024x1024': _a > 1 ? '1536x1024':'1024x1536',
    }
  }
  if(props.isChat){
    _data.btnLoading=false
    emit('change', obj, modelInfo.value.value, 'example')
  } else {
     exampleSend(obj, modelInfo.value.value, 'example')
  }
}
const exampleSend = async (item, model, type) => {
  if (userStore.points < sendPoints.value) {
    showTipConfirm()
    return
  }
  let _sessionIdx = -1
  let formData = new FormData()
  formData.append('userid', userStore.userinfo.userId)
  formData.append('name', item.text)
  const chatRow = await newConver(formData)
  _sessionIdx = chatRow.data.id;

  const chatData = {
    "conversation_id":_sessionIdx,
    ...item
  }
  let res = null
  try {
    if (model === 'gemini') {
      res = await postGemini(chatData)
    } else  if (model === 'gpt-4o-image') {
      res = await postChatGPT(chatData)
    }  else if (item.image_urls.length>0) {//奇画、flex图生图
      let _n = gcd(item.width, item.height)
      res = await postFluxKonTextCombined({
        prompt:  item.text,
        "image_paths": item.image_urls,
        "conversation_id": _sessionIdx, // 绘画id
        aspect_ratio:  item.width / _n + ':' + item.height / _n,
        "stream": false
      }, model)
    } else {
      if (model === 'flex') res = await postCombined(chatData)
      if (model === 'qiHua') res = await postVolcengine(chatData)
    }
    _data.btnLoading=false
    if (res && res.data) {
      router.push({path: '/chat', query: {chatId: _sessionIdx}})
    }
  } catch (e) {
    _data.btnLoading=false
  }
}
const showTipConfirm = () => {
  const _Modal = Modal.confirm({
    closable: true,
    maskClosable: true,
    centered: true,
    title: '算力不足！',
    content: '您的算力已不足，如需继续请先购买算力或开通会员',
    okText: '去购买',
    okType: 'danger',
    class: 'tips-modal',
    cancelText: '取消',
    width: '500px',
    onOk() {
      emitter.emit('show-vip-modal', 'vip') //产品替换鼠标移动全局监听
    },
    onCancel(obj) {
      _data.btnLoading=false
      _Modal.destroy();
    },
  });
};
const refreshWidth = () => {

  nextTick(() => {
    const {offsetWidth,offsetHeight} = document.body
    const {offsetHeight:eHeight} = exampleRef.value
    const {aspectRatio} = imageInfo.value
    let height =  offsetHeight - 280
    if(height < eHeight) height = eHeight
    let maxWidth =  offsetWidth *0.8 - 580
    let width = height * aspectRatio
    if(aspectRatio > 1 &&width > maxWidth) {
        width = maxWidth
        height = width / aspectRatio
    }
      imageStyle.value = {
        height: height + 'px',
        width: width + 'px'
      }
     modalWidth.value = width + 500 + 100 + 'px'
  })
  _data.loading = false;
}
function open(item) {
  _data.visible = true;
  _data.loading = true;
  getImageList(item.image_path)
  modelInfo.value = getModelByKey(item.generation_method)
  var img = new Image()
  img.onload = function() {
    imageInfo.value.width = img.naturalWidth
    imageInfo.value.height = img.naturalHeight
    imageInfo.value.aspectRatio = img.naturalWidth / img.naturalHeight
    refreshWidth()
  }
  img.src = getChildList(item.image_path_res)
  imageInfo.value = item;
}

function hide() {
  _data.visible = false;
}

defineExpose({
  open,
  hide
})

</script>

<style lang="less" scoped>
.member-content {
  .cell-item {
    width: 100%;
    // margin-bottom: 18px;
    background: #1C1C1C;
    border-radius: 12px 12px 12px 12px;
    overflow: hidden;
    box-sizing: border-box;
    padding: 20px;
    position: relative;
    color: #999999;

    .left-image-box {
      //width: 60%;
      //background: #48505D;
      padding: 20px;
      border-radius: 8px;
     // height: calc(100vh - 240px);

      .image-box {
        position: relative;
        max-height: 100%;

        img {
          // border-radius: 12px 12px 0 0;
          //max-width: 100%;
          //max-height: calc(100vh - 280px);
          display: block;
          border-radius: 8px;
        }
      }
    }

    .example-info {
      width: 500px;
      padding: 10px;

      .title {
        padding: 10px 0;

      }

      .modal-name {
        background: @bg-page-two-color;
        border-radius: 8px;
        padding: 10px;

        .iconfont {
          line-height: 32px;
          font-size: 32px;
          color: #4065C6;
          padding-right: 10px;
          margin-right: 10px;
          border-right: 1px solid #2E2E2E;
        }
        .t2{
          font-size: 12px;
          color: #5A5A5A;
        }
      }

      .auxiliary-image {
        padding: 10px;
        border-radius: 8px;
        //background: #252525;

        .auxiliary-image-item {
          display: inline-block;
          img {
            background: @bg-page-color;
            height: 160px;
            border-radius: 8px;
            margin-right:  10px;
          }
        }
      }

      .auxiliary-text {
        padding: 10px;
        border-radius: 8px;
        background: @bg-page-two-color;
        &.text{
          background: @bg-page-color;
          font-size: 14px;
        }
      }
      .image-table{
        margin: 10px 0;
        border-top: 1px solid #2E2E2E;
        border-left: 1px solid #2E2E2E;
        text-align: center;
        border-radius: 8px;
        .flex-1{
          padding: 5px;
          border-bottom: 1px solid #2E2E2E;
          border-right: 1px solid #2E2E2E;
        }
      }
      .btn {
        margin-top: 30px;
        width: 200px;
        height: 40px;
        font-size: 16px;
        border-radius: 8px;
        border: 0;
        background: @btn-bg-two-color;
      }

      .like {
        padding: 5px 10px;
        >div{
          margin: 0 10px;
          padding: 10px;
          border-radius: 21px;
          min-width: 42px;
          border: 1px solid #5A5A5A;
          cursor: pointer;
          .iconfont {
            line-height: 20px;
            font-size: 20px;
          }
          &.like-box{
            width: 100px;
            height: 42px;
            .iconfont {
              margin-right: 10px;
            }
            &.active {
              color: #ff4479;
            }
          }
        }
      }
    }
  }
}
</style>
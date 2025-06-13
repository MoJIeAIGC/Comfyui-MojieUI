<template>
  <div class="home-wp">
    <leftMenu ref="leftMenuRef" :tab="routeTab" @change="chatChange"/>
    <div class="center">
      <div class="select-model">
        <mModelSelect ref="modelSelectRef"/>
      </div>
      <div ref="msgListRef" class="list" @wheel="handleScroll">
        <template v-for="(item, index) in _data.msgList">
          <div class="item myself">
            <div class="ct">
              <div class="img-list">
                <mImgShow class="img" v-for="imgItem in initItemToArray(item)"
                          type="right" @toolClick="toolClick" :src="imgItem"/>
              </div>
              <div class="msg">
                <div class="prompt line3" v-if="!item.edtFlag" :title="getPromptText(item)">{{ getPromptText(item) }}</div>
                <div class="prompt edt-prompt" v-if="item.edtFlag">
                  <a-textarea class="ipt flex-1"
                              v-model:value="item.edtText"
                              :autoSize="true"
                              :maxlength="1000"
                              :bordered="false"
                  />
                  <div class="text-right">
                    <a-button type="primary" size="small" shape="round" @click="cancelEdtItem(item)">
                      取消
                    </a-button>
                    <a-button shape="round" size="small" class="send-btn items-center justify-center" @click="regenerateSend(item)">
                      <template #icon>
                        <i class="iconfont icon-fasong"></i>
                      </template>
                      发送({{item.pointText}})
                    </a-button>
                  </div>
                </div>
                <!--                <div class="footer-setting">1:1 - 1024:1024  |  数量:1  |  seed:46496 |</div>-->
                <div class="footer-setting">

                  <span class="footer-setting-btn">数量: {{item.task_info && item.task_info.input_data && item.task_info.input_data.batch_size ? item.task_info.input_data.batch_size : 1 }}</span>
<!--                  <span class="footer-setting-btn" v-if="getStatus(item)==='completed' || initItemToArray(item).length===0"  @click="copyText(getPromptText(item))">复制</span>-->
<!--                  <span class="footer-setting-btn" v-if="getStatus(item)==='completed'|| initItemToArray(item).length===0"  @click="edtItem(item)">编辑</span>-->
                  <span class="footer-setting-btn"  @click="delChatItem(item)">删除</span>
                </div>
              </div>
            </div>
          </div>
          <div class="item">
            <div class="ct">
              <div class="msg">
                <div class="image-box">
                  <div class="img-list">
                    <div class="prompt flex justify-start items-center">
                      <img src="../../assets/image/chat.png">
                      <div class="model_used">{{ getKey(item.model_used) }}</div>
                      <div class="model_time" v-if="item.task_info&&item.task_info.updated_at">
                        {{ dayjs(new Date(item.task_info.updated_at).getTime()).format('YYYY-MM-DD HH:mm:ss') }}
                      </div>
                    </div>
                    <div class="img-tip line3" :title="getPromptText(item)">{{ getPromptText(item) }}</div>
                    <mTaskView v-if="getStatus(item)=== 'pending'||getStatus(item)=== 'processing'" :row="item"
                               :queue-list="_data.queueList" @cancel="getChatList"></mTaskView>
                    <div v-if="getStatus(item)=== 'pending'||getStatus(item)=== 'processing'" class="thinkingIcon">
                      <a-spin tip="图片生成中..."></a-spin>
                    </div>
                    <div v-if="getStatus(item)=== 'failed'||getStatus(item)=== 'cancelled'" class="error-tip">
                      <a-result
                          status="error"
                          :sub-title="getStatus(item)=== 'cancelled'?'已取消':'生成失败'" >
                        <template #icon>
                          <picture-filled size="50"/>
                        </template>
                        <!--                        <template #extra>-->
                        <!--                          <a-button type="link" @click="regenerate(item)" :disabled="_data.gptThinking">重新生成</a-button>-->
                        <!--                        </template>-->
                      </a-result>
                    </div>
                    <template v-if="getStatus(item)==='completed'">
                      <mImgShow class="img"
                                @toolClick="toolClick"
                                @retry="regenerate(item,rItem)"
                                v-for="rItem in getResult(item)"
                                :length="getResult(item).length"
                                :src="rItem"/>
                    </template>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
        <div class="item" v-if="(showModel || _data.msgList.length===0)&&tipsObject&&tipsObject.welcome">
          <div class="ct">
            <div class="msg">
              <div class="image-box">
                <div class="img-list">
                  <div class="prompt flex justify-start items-center">
                    <img src="../../assets/image/chat.png">
                    <div class="model_used">{{ tipsObject.welcome }}</div>
                  </div>
                  <div class="welcome-tip" v-for="tItem in tipsObject.textList">
                    <span>{{ tItem.title }}:&nbsp;&nbsp;</span>{{ tItem.text }}
                  </div>
                  <div class="operate-tip">
                    <div class="operate-tip-item" v-for="tItem in tipsObject.operateList"
                         @click="quickSend(tItem.info)">{{ tItem.text }}
                      <right-outlined/>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="bottom flex justify-center items-center" :class="{'has-file':_data.fileList.length>0}">
        <div class="send-box" :class="drapClass" @drop.prevent="handleDrop" @dragover.prevent="drapClassChange('over')"
             @dragenter.prevent="drapClassChange('enter')" @dragleave="drapClassChange('leave')">
          <div class="ipt-box flex">
            <a-textarea class="ipt flex-1"
                        v-model:value="_data.msgText"
                        :bordered="false"
                        placeholder="给奇画发送信息，回车发送，Alt+回车换行"
                        :auto-size="autoSize"
                        :maxlength="1000"
                        @pressEnter.prevent="sendChat($event)"/>
            <!--            <a-input class="ipt flex-1" type="" v-model:value="_data.msgText" :bordered="false" placeholder="给奇画发送信息"  @pressEnter.prevent="sendChat($event)" />-->
            <div class="btn-list flex justify-end items-center">
              <div class="raw-image">
                <mResolutionSelect></mResolutionSelect>
              </div>
              <div class="raw-image" v-if="userStore.modelType==='flex'&&_data.fileList.length===0">
                <mGeneratorSelect></mGeneratorSelect>
              </div>
              <a-tooltip color="#121212">
                <template #title>{{pointsText}}</template>
                <a-button type="primary" shape="round" class="send-btn items-center justify-center"
                          :disabled="_data.gptThinking" @click="sendChat" :loading="_data.gptThinking">
                  <template #icon>
                    <i class="iconfont icon-fasong"></i>
                  </template>
                  发送({{pointsText}})
                </a-button>
              </a-tooltip>
            </div>
            <div class="upload-box">
              <div class="flex justify-start items-start">
                <a-upload
                    :disabled="_data.fileList.length>=_data.maxUpFileCount"
                    accept="image/*"
                    :showUploadList="false"
                    list-type="picture"
                    :beforeUpload="previewFile">
                  <a-tooltip color="#121212">
                    <template #title>上传图片</template>
                    <a-button :disabled="_data.fileList.length>=_data.maxUpFileCount" shape="circle">
                      <PlusOutlined/>
                    </a-button>
                  </a-tooltip>
                </a-upload>
              </div>
            </div>
            <div class="up-file-list flex justify-center items-start" v-if="_data.fileList.length > 0">
              <div v-for="(imgItem,index) in _data.fileList" :key="index" class="flex justify-center items-start">
                <div class="img flex justify-center items-center">
                  <a-spin size="small" v-if="imgItem.loading===1" :spinning="imgItem.loading===1" tip="上传中..."/>
                  <div class="loading-tips" v-if="imgItem.loading===-1">
                    上传失败
                    <a-button type="link" size="small" @click="retryFile(imgItem.file,index)">重试</a-button>
                    <br/>或
                    <a-button type="link" size="small" @click="delFileList(index)">取消</a-button>
                    上传
                  </div>
                  <img v-db-click-img v-if="imgItem.url" :src="imgItem.url" alt=""/>
                </div>
                <CloseCircleOutlined class="close-icon" v-if="imgItem.url" @click="delFileList(index)"/>
              </div>
            </div>
          </div>
        </div>
        <div class="msg-tips">图像生成请遵守法律法规，暴力/色情/名人/版权IP 提示词可能会导致生成失败。</div>
      </div>
    </div>

    <rightTool ref="rightToolRef" :chatId="_data.sessionIdx" :tab="routeTab" @no-points="showTipConfirm"></rightTool>
<!--    <vipModal ref="vipModalRef" @change="toPionts"></vipModal>-->
<!--    <pointsModal ref="pointsModalRef"></pointsModal>-->
<!--    <vipOrPointsModal ref="pointsModalRef"></vipOrPointsModal>-->
    <ExampleModel ref="exampleModalRef" is-chat @change="exampleSend"></ExampleModel>
  </div>
</template>

<script setup>
import {nextTick, reactive, ref, watch, computed, onMounted, onUnmounted, createVNode} from 'vue'
import {useRoute} from 'vue-router'
import {message, Modal, notification} from "ant-design-vue";
import {
  PlusOutlined,
  CloseCircleOutlined,
  PictureFilled,
  RightOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons-vue';
import mModelSelect from "@/components/mModelSelect/index.vue";
import mResolutionSelect from "@/components/mResolutionSelect/index.vue";
import mGeneratorSelect from "@/components/mGeneratorSelect/index.vue";
import rightTool from "@/components/modules/rightTool.vue";
import mImgShow from "@/components/mImgShow/index.vue";
import mTaskView from "@/components/mTaskView/index.vue";
import leftMenu from "@/components/modules/leftMenu.vue"
// import vipModal from "@/components/modules/userTools/vipModal.vue";
// import pointsModal from "@/components/modules/userTools/pointsModal.vue";
// import vipOrPointsModal from "@/components/modules/userTools/vipOrPointsModal.vue";
import ExampleModel from "@/components/exampleModel/index.vue"

import {resolutionList, deductionRules, modelMappingLabel} from '@/options/model.js';
import {useUserStore} from '@/store/userStore';
import {uploadImg} from "@/api/upload.js";
import {base64UrlToFile, compressFile, gcd} from "@/utils/utils.js";
import {
  getUserImages,
  postChatGPT,
  postGemini,
  newConver,
  imageQueue,
  postCombined,
  postVolcengine,
  postChatRetry, delChat, postFluxKonTextCombined
} from "@/api/chat.js";
import {getUserSeek} from "@/api/pay.js";
import {welcomeList} from "@/options/welcome.js";
import {httpIndex} from "@/options/model.js";
import emitter from "@/utils/emitter.js";
import dayjs from "dayjs";
import {useChatStore} from "@/store/chatStore.js";
import {isHttp, isImageFile} from "@/utils/utils.js";
import {getTranslateToEn} from "@/api/product.js";
const route = useRoute()
const userStore = useUserStore();
const modelSelectRef = ref();
// const vipModalRef = ref();
// const pointsModalRef = ref();
const chatStore = useChatStore();
const routeTab = ref('chat');
const drapClass = ref('');
const showModel = ref(false);
watch(() => route.query, (query, oldParams) => {
  routeTab.value = query.type ? query.type : 'chat'
}, {immediate: true});
watch(() => userStore.modelType, (query, oldParams) => {
  showModel.value =true
  _data.scrollHeight = -1
  nextTick(() => {
    setScrollTop();
  })
});
const msgListRef = ref();
const timer = ref();
const leftMenuRef = ref();
const rightToolRef = ref();
const autoSize = {minRows: 1, maxRows: 2}
const exampleModalRef = ref()
const _data = reactive({
  isScroll: false,
  hasTask: false,
  queueList: [],
  maxUpFileCount: 3, //每次对话可上传图片数量
  sessionIdx: -1, // 当前会话下标
  gptThinking: false,
  msgText: '',
  msgList: [],
  fileList: [],
  scrollHeight: -1,
  timer: null,
  timer2: null
})
onMounted(() => {
  emitter.on('refresh-chat-list', (id) => {
    _data.scrollHeight = -1
    _data.isScroll = true
    _data.sessionIdx = id
    showModel.value =false
    getChatList()
  });
  emitter.on('open-example', (item) => {
    openExampleModal(item)
  });
})

onUnmounted(() => {
  if (_data.timer2) clearTimeout(_data.timer2);
  if (_data.timer) clearTimeout(_data.timer);
  if (timer.value) clearTimeout(timer.value);
  emitter.off('refresh-chat-list')
  emitter.off('open-example')
})
const tipsObject = computed(() => {
  return welcomeList.filter(item => item.model === userStore.modelType)[0] || {}
});
const _deductionRules = computed(() => {
  const isVip = userStore.vipInfo&&userStore.vipInfo.level
  return  isVip ? deductionRules.vip : deductionRules.default
});
const sendPoints = computed(() => {
    const _Rules = _deductionRules.value
    let _modelType = userStore.modelType
    let points = _modelType === 'gpt-4o-image' ? _Rules['gpt-4o-image'] : _Rules['flex']
    if (_modelType === 'flex') {
      points = points * parseInt(chatStore.generatorType)
      if(_data.fileList.length > 0) {
        points =  _Rules['flux_kontext_pro_2']
      }
    }
    if (_modelType === 'qiHua') {
      if(_data.fileList.length > 0) {
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
  return  sendPoints.value +'算力'
});
const getPoints = (item) => {
  let _modelType = 'flex',number =1,_list = initItemToArray(item)
  if(item.task_info && item.task_info.input_data && item.task_info.input_data.batch_size ) number = item.task_info.input_data.batch_size
  const key = item.model_used
  if (key && (key.indexOf('gpt') !== -1 || key.indexOf('GPT') !== -1)) _modelType = 'gpt-4o-image'
  if (key&&(key.indexOf('volcengine')!==-1||key.indexOf('dou')!==-1)) _modelType =  'qiHua'

  const _Rules = _deductionRules.value
  let points = _modelType === 'gpt-4o-image' ? _Rules['gpt-4o-image'] : _Rules['flex']
  if (_modelType === 'flex') {
    points = points * parseInt(number)
    if(_list.length > 0) {
      points =  _Rules['flux_kontext_pro_2']
    }
  }
  if (_modelType === 'qiHua') {
    if(_list.length > 0) {
      points =_Rules['flux_kontext_pro_1']
    } else {
      points = _Rules['qiHua']
    }
  }
  const isVip = userStore.vipInfo&&userStore.vipInfo.level
  if (isVip && points ===0) return '会员免费'
  return  points +'算力'
}
const getKey = (key) => {
  let flexLabel =  modelMappingLabel.flex
  const obj = {
    'ai_product': '迁移替换',
    'multi_image': flexLabel,
    'clue_image': flexLabel,
    'ai_image': flexLabel,
    'ai_text': flexLabel,
    'white':flexLabel,
    'clue':flexLabel,
    'flux_kontext_pro_2':  flexLabel,
    'flux_kontext_pro_1': modelMappingLabel.qiHua,
    'complete_redrawing':  flexLabel,
    'wide_picture': '智能扩图',
    'fine_detail': '局部重绘',
    'internal_supplementation': '内补消除',
    'internal_supplementation_and_removal': '内补消除',
    '色彩调节模型': '色彩调节'
  }
  if (obj[key]) return obj[key];
  if (key && (key.indexOf('gpt') !== -1 || key.indexOf('GPT') !== -1)) {
    return modelMappingLabel.gptLabel
  }
  if (key && (key.indexOf('gemini') !== -1)) {
    return 'Gemini-image'
  }
  if (key && (key.indexOf('flex') !== -1 || key.indexOf('ai_') !== -1)) {
    return flexLabel
  }
  if (key && (key.indexOf('volcengine') !== -1)) {
      return modelMappingLabel.qiHua
  }
  return '未知'
}
const getModalType = (key) => {
  if (key && (key.indexOf('gpt') !== -1 || key.indexOf('GPT') !== -1)) {
    return 'gpt-4o-image'
  }
  if (key && (key.indexOf('volcengine') !== -1 || key.indexOf('qiHua') !== -1) ||key === 'flux_kontext_pro_1') {
    return 'qiHua'
  }
  return 'flex'
}
const drapClassChange = (type) => {
  drapClass.value = type
}
const handleDrop = (event) => {
  drapClass.value = ''
  let url = event.dataTransfer.getData('text/plain'); // 获取数据
  if (url) {
    if (_data.fileList.length >= _data.maxUpFileCount) {
      message.error('每次对话最多只能选择三张图片')
      return
    }
    if (isHttp(url)) {
      if(url.indexOf(httpIndex)===-1){
        message.error('您拖拽的图片链接非本网站的链接，请先下载后再拖入下载后的图片')
        return
      }
      _data.fileList.push({loading: 0, url: url})
    } else {
      if (url.indexOf('base64') !== -1) {
        const uFile = base64UrlToFile(url)
        previewFile(uFile)
        return
      }
      message.warning("未识别的图片链接")
    }
    return;
  }
  const files = event.dataTransfer.files;
  if (files.length > 1) return message.warning("只能拖入一个文件")
  if (files.length === 1) {
    if (isImageFile(files[0].type)) {
      previewFile(files[0])
    } else {
      message.warning("拖入的文件不是图片格式")
    }
  }
}
const delChatItem = (item) => {
  Modal.confirm({
    title: '提示',
    icon: createVNode(ExclamationCircleOutlined),
    content: `确定删除当前消息么`,
    onOk() {
      delChat(item.id).then((res) => {
        notification.success({
          message: '提示',
          description: '删除成功'
        });
      }).finally(()=>{
        getChatList()
      })
    },
    onCancel() {
    },
  });
}
const getChatList = () => {
  if (timer.value) clearTimeout(timer.value);
  getUserImages({userid: userStore.userinfo.userId, sessionid: _data.sessionIdx}).then(res => {
    _data.msgList = res.data && res.data[_data.sessionIdx] ? res.data[_data.sessionIdx] : []
    _data.gptThinking = false;
    const hasProcessing = _data.msgList.filter(item => getStatus(item) === 'pending' || getStatus(item) === 'processing').length > 0
    searchPoints()
    if (hasProcessing) {
      getImageQueue()
      if (timer.value) clearTimeout(timer.value);
      timer.value = setTimeout(() => {
        getChatList()
      }, 30 * 1000)
    }
    nextTick(() => {
      setScrollTop();
    })
  })
}
const getPromptText = (item) => {
  if (item.task_info && item.task_info.input_data && item.task_info.input_data.metadata && item.task_info.input_data.metadata.add_new_data) {
    let obj = JSON.parse(item.task_info.input_data.metadata.add_new_data);
    let text = obj.text
    if (obj.templateText) text = obj.text + '\n' + obj.templateText
    if (text) return text
    const _obj = {
      'ai_product': '替换产品',
      // 'wide_picture':'扩图',
      // 'fine_detail':'局部重绘',
      // 'internal_supplementation':'内补',
      // 'internal_supplementation_and_removal':'消除',
      // '色彩调节模型':'色彩调节'
    }
    return _obj[item.model_used] || item.prompt
  }
  return item.prompt
}
const getImageQueue = () => {
  if (_data.timer2) clearTimeout(_data.timer2);
  imageQueue().then(res => {
    _data.queueList = res.data.queue_tasks
    for (let msgItem of  _data.msgList) {
        let queue =_data.queueList.find(taskItem => taskItem.task_id === msgItem.comfyUI_task_id)
         if(queue){
           renderComplete()
           break
         }
    }
    if (res.data.queue_tasks.length === 0 && _data.timer2) {
      clearTimeout(_data.timer2);
    }
  })
}
const renderComplete = () => {;
    if (_data.timer2) clearTimeout(_data.timer2);
    _data.timer2 = setTimeout(() => {
      getImageQueue()
    }, 5 * 1000)
}
const handleScroll = (e) => {
  if (_data.isScroll) return
  if ((msgListRef.value.scrollHeight - msgListRef.value.offsetHeight) < (msgListRef.value.scrollTop + 100)) {
    _data.scrollHeight = -1
  } else {
    _data.scrollHeight = msgListRef.value.scrollTop
  }
}

const chatChange = (id) => {
  _data.scrollHeight = -1
  _data.isScroll = true
  if (_data.timer2) clearTimeout(_data.timer2);
  showModel.value = false
  if (id === -1) {
    _data.sessionIdx = id
    _data.msgList = []
  } else {
    if (id !== _data.sessionIdx) {
      _data.sessionIdx = id
      getChatList()
    }
  }
}

const addChatFile = (imgSrc) => {
  console.log(imgSrc)
  // if(imgSrc === 'db'){
  //    if( _data.timer) clearTimeout(_data.timer)
  //     return;
  // }
  // if( _data.timer) clearTimeout(_data.timer)
  // _data.timer = setTimeout(()=>{
  //   if (_data.fileList.length >= _data.maxUpFileCount) {
  //     message.error('每次对话最多只能选择三张图片')
  //     return
  //   }
  //   _data.fileList.push({loading: 0, url: imgSrc})
  // },300)
}
const toolClick = (item, url) => {
  rightToolRef.value.setType(item, url)
}
const quickSend = (item) => {
  //  if(text) _data.msgText = text
  // sendChat()
  exampleModalRef.value.open(item)
}
const cancelEdtItem = (item) => {
  item.edtFlag = false
  item.edtText = getPromptText(item)
}
const edtItem = (item) => {
  item.edtFlag = true
  item.edtText = getPromptText(item)
  item.pointText = getPoints(item)
}
const copyText = (text) => {
  try {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
    message.success('复制成功')
  } catch (error) {
    message.error('复制失败')
  }
}
const initItemToArray = (item) => {
  let str = item.image_list
  let _list = [], maskList = []
  if (item.model_used === 'ai_product') {
    if (item.task_info && item.task_info.input_data && item.task_info.input_data.metadata && item.task_info.input_data.metadata.add_new_data) {
      let obj = JSON.parse(item.task_info.input_data.metadata.add_new_data);
      if (obj.url) _list = [obj.url]
    }
    // if(item.task_info&&item.task_info.input_data&&item.task_info.input_data.mask_url) {
    //   maskList = [item.task_info.input_data.mask_url]
    // }
  }
  // if(item.task_info&&item.task_info.input_data&&item.task_info.input_data.mask_url) {
  //   maskList = [item.task_info.input_data.mask_url]
  // }
  //const arrayStr = 'pending,failed,completed'
  if (!str || str === 'pending') return _list.concat(maskList)
  if (!isHttp(str)) return []
  if (Array.isArray(str)) return _list.concat(str).concat(maskList)
  return _list.concat(str.split(',')).concat(maskList)
}
const getStatus = (item) => {
  if (item.task_info && item.task_info.status ) {
    return  item.task_info.status
  }
  return item.status
}
const getResult = (item) => {
  if (item.task_info && item.task_info.result && item.task_info.result.image_urls) {
    return item.task_info.result.image_urls
  }
  if (item.image_url) return item.image_url.split(',')
  return []
}
const initStringToArray = (str) => {
  //const arrayStr = 'pending,failed,completed'
  if (!str || str === 'pending') return []
  if (Array.isArray(str)) return str
  if (!isHttp(str)) return []
  return str.split(',')
}
// const toPionts = () => {
//   pointsModalRef.value.open()
// }
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
      //pointsModalRef.value.open()
    },
    onCancel(obj) {
       _Modal.destroy();
    },
  });
};

const exampleSend = async (item, model, type) => {
  let _points =  _deductionRules.value.flex
  if (model && (model.indexOf('gpt') !== -1 || model.indexOf('GPT') !== -1)) _points =  _deductionRules.value['gpt-4o-image']
  if (model&&(model.indexOf('volcengine')!==-1||model.indexOf('dou')!==-1)) _points =  _deductionRules.value['qiHua']

  if (userStore.points < _points) {
    showTipConfirm()
    return
  }
  exampleModalRef.value.hide()
  if (_data.sessionIdx === -1) {
    // 清空历史
    _data.msgList = [];
    // 获取摘要
    let formData = new FormData()
    formData.append('userid', userStore.userinfo.userId)
    formData.append('name', item.text)
    const chatRow = await newConver(formData)
    leftMenuRef.value.changeChat(chatRow.data)
    _data.sessionIdx = chatRow.data.id;
  }
  if (_data.gptThinking) return;

  _data.gptThinking = true;
  _data.scrollHeight = -1
  _data.isScroll = true
  const chatData = {
    "conversation_id": _data.sessionIdx,
    ...item
  }
  let res = null
  try {
    if (model === 'gemini') {
      res = await postGemini(chatData)
    } else if (model === 'gpt-4o-image') {
      res = await postChatGPT(chatData)
    }   else  if (item.image_urls.length>0) {//奇画、flex图生图
      let _n = gcd(item.width, item.height)
      res = await postFluxKonTextCombined({
        prompt:  item.text,
        "image_paths": item.image_urls,
        "conversation_id": _data.sessionIdx, // 绘画id
        "stream": false,
        aspect_ratio:  item.width / _n + ':' + item.height / _n,
      }, model)
    } else {
      if (model === 'flex') res = await postCombined(chatData)
      if (model === 'qiHua') res = await postVolcengine(chatData)
    }
    if (res && res.data) {
      getChatList()
    }
    showModel.value =false
  } catch (e) {
    showModel.value =false
  }
}
//重新发送
const regenerate = async (item, retrySrc) => {
  let _points =  _deductionRules.value.flex
  const key = item.model_used
  if (key && (key.indexOf('gpt') !== -1 || key.indexOf('GPT') !== -1)) _points =  _deductionRules.value['gpt-4o-image']
  if (key&&(key.indexOf('volcengine')!==-1||key.indexOf('dou')!==-1)) _points =  _deductionRules.value['qiHua']
  if (key === 'ai_product') _points = _deductionRules.value.ai_product
  if (userStore.points < _points) {
    showTipConfirm()
    return
  }
  if (item.comfyUI_task_id) {
    postChatRetry(item.comfyUI_task_id).then(res => {
      showModel.value =false
      getChatList()
    })
    return;
  }
  if (_data.gptThinking) return;
  const _imageInfo = new Image()
  _imageInfo.onload = async () => {
    // imageInfo.value.width = imageInfo.naturalWidth
    // imageInfo.value.height = imageInfo.naturalHeight
    const _aspectRatio = _imageInfo.naturalWidth / _imageInfo.naturalHeight
    const _list = initStringToArray(item.image_list)
    const model = getModalType(key)
    let obj = {}
    let _obj2 = {
      width:_imageInfo.naturalWidth,
      height: _imageInfo.naturalHeight,
      quantity: 1,
      image_urls: _list,
      text:  item.prompt, //图像生成描述文本
    }
    if (model === 'flex') {
      obj = {
        description: item.prompt,
        ..._obj2,
        add_new_data: JSON.stringify({
          text: item.prompt
        }),
      }
      try {
        if(_list.length===0){
          let _resEn = await getTranslateToEn( item.prompt)
          if (_resEn.data && _resEn.data.translated_text) obj.description = _resEn.data.translated_text
        }
      } catch (err) {
        console.log(err)
      }
    }
    if (model === 'qiHua') {
      obj = {
        "stream": false,
        ..._obj2,
      }
    }
    if (model === 'gpt-4o-image') {
      obj = {
        "model": 'gpt-4o-image',
        image_paths: _list,
        "stream": false,
        operation_type: _list.length>0 ?'edit':'generate',
        "prompt": item.prompt, //图像生成描述文本
        "text": item.prompt, //图像生成描述文本
        size:_aspectRatio === 1? '1024x1024': _aspectRatio > 1 ? '1536x1024':'1024x1536',
      }
    }
    if (_data.gptThinking) return;

    _data.gptThinking = true;
    _data.scrollHeight = -1
    _data.isScroll = true
    const chatData = {
      "conversation_id": _data.sessionIdx,
      ...obj
    }
    let res = null
    try {
      if (model === 'gemini') {
        res = await postGemini(chatData)
      } else if (model === 'gpt-4o-image') {
        res = await postChatGPT(chatData)
      }  else if (_list.length>0) {//奇画、flex图生图
        let _n = gcd( _imageInfo.naturalWidth, _imageInfo.naturalHeight)
        res = await postFluxKonTextCombined({
          prompt:   item.prompt,
          "image_paths": _list,
          "conversation_id": _data.sessionIdx, // 绘画id
          "stream": false,
          aspect_ratio:  _imageInfo.naturalWidth / _n + ':' + _imageInfo.naturalHeight / _n,
        }, model)
      } else {
        if (model === 'flex') res = await postCombined(chatData)
        if (model === 'qiHua') res = await postVolcengine(chatData)
      }
      if (res && res.data) {
        getChatList()
      }
      _data.gptThinking = false;
      showModel.value =false
    } catch (e) {
      _data.gptThinking = false;
      showModel.value =false
    }
  }
  _imageInfo.src = retrySrc
}
const regenerateSend = async (item) => {
  let _points =  _deductionRules.value.flex
  const key = item.model_used
  if (key && (key.indexOf('gpt') !== -1 || key.indexOf('GPT') !== -1)) _points =  _deductionRules.value['gpt-4o-image']
  if (key&&(key.indexOf('volcengine')!==-1||key.indexOf('dou')!==-1)) _points =  _deductionRules.value['qiHua']
  if (userStore.points < _points) {
    showTipConfirm()
    return
  }
  if (_data.gptThinking) return;
  const _imageInfo = new Image()
  _imageInfo.onload = async () => {
    const _aspectRatio = _imageInfo.naturalWidth / _imageInfo.naturalHeight
    const _list = initStringToArray(item.image_list)
    const model = getModalType(key)
    let obj = {}
    // item.edtFlag = true
    // item.edtText = getPromptText(item)
    // item.pointText = getPoints(item)
    let _obj2 = {
      width:_imageInfo.naturalWidth,
      height: _imageInfo.naturalHeight,
      quantity: 1,
      image_urls: _list,
      text:  item.edtText, //图像生成描述文本
    }
    if (model === 'flex') {
      obj = {
        description: item.edtText,
        ..._obj2,
        add_new_data: JSON.stringify({
          text: item.edtText
        }),
      }
      try {
        if(_list.length===0){
          let _resEn = await getTranslateToEn( item.edtText)
          if (_resEn.data && _resEn.data.translated_text) obj.description = _resEn.data.translated_text
        }
      } catch (err) {
        console.log(err)
      }
    }
    if (model === 'qiHua') {
      obj = {
        "stream": false,
        ..._obj2,
      }
    }
    if (model === 'gpt-4o-image') {
      obj = {
        "model": 'gpt-4o-image',
        image_paths: _list,
        "stream": false,
        operation_type: _list.length>0 ?'edit':'generate',
        "prompt": item.edtText, //图像生成描述文本
        "text": item.edtText, //图像生成描述文本
        size:_aspectRatio === 1? '1024x1024': _aspectRatio > 1 ? '1536x1024':'1024x1536',
      }
    }
    if (_data.gptThinking) return;

    _data.gptThinking = true;
    _data.scrollHeight = -1
    _data.isScroll = true
    const chatData = {
      "conversation_id": _data.sessionIdx,
      ...obj
    }
    let res = null
    try {
      if (model === 'gemini') {
        res = await postGemini(chatData)
      } else if (model === 'gpt-4o-image') {
        res = await postChatGPT(chatData)
      }  else if (_list.length>0) {//奇画、flex图生图
        let _n = gcd( _imageInfo.naturalWidth, _imageInfo.naturalHeight)
        res = await postFluxKonTextCombined({
          prompt:   item.edtText,
          "image_paths": _list,
          "conversation_id": _data.sessionIdx, // 绘画id
          "stream": false,
          aspect_ratio:  _imageInfo.naturalWidth / _n + ':' + _imageInfo.naturalHeight / _n,
        }, model)
      } else {
        if (model === 'flex') res = await postCombined(chatData)
        if (model === 'qiHua') res = await postVolcengine(chatData)
      }
      if (res && res.data) {
        getChatList()
      }
      _data.gptThinking = false;
      showModel.value =false
    } catch (e) {
      showModel.value =false
      _data.gptThinking = false;
    }
  }
  _imageInfo.src = getResult(item)[0]
}

// 发送会话内容
async function sendChat(event) {
  // alt+enter换行
  if (event && event.altKey) {
    _data.msgText += '\n';
    return;
  }
  let _modelType = userStore.modelType
  if (userStore.points < sendPoints.value) {
    showTipConfirm()
    return
  }
  if (!_data.msgText) {
    message.error('请输入对话内容')
    return
  }
  if (_data.msgText.length < 5) {
    message.error('输入的内容不能少于5字')
    return
  }
  if (!_data.msgText.length || _data.gptThinking) return;
  // const msgText = _data.msgText.replace(/\\n/g,' ')
  const msgText = _data.msgText
  // 新建默认会话
  if (_data.sessionIdx === -1) {
    // 清空历史
    _data.msgList = [];
    // 获取摘要
    let formData = new FormData()
    formData.append('userid', userStore.userinfo.userId)
    formData.append('name', msgText)
    const chatRow = await newConver(formData)
    leftMenuRef.value.changeChat(chatRow.data)
    _data.sessionIdx = chatRow.data.id;
  }
  _data.gptThinking = true;
  let msgTextEn = ''
  if (_modelType === 'flex') {
    try {
      if(_data.fileList.length===0) {
        let _resEn = await getTranslateToEn(msgText)
        if (_resEn.data && _resEn.data.translated_text) msgTextEn = _resEn.data.translated_text
      }
    } catch (err) {
      console.log(err)
    }
  }
  const geminiData = {
    "aspect_ratio": "Free",
    "temperature": 1,
    'enable_long_context': false
  }
  //image_ChatGPT_OPENAI_API_product

  const chatData = {
    "model": _modelType,
    operation_type: _data.fileList.length > 0 ? 'edit' : 'generate',
    image_paths: _data.fileList.map((item) => {
      return item.url
    }),
    "stream": false,
    "conversation_id": _data.sessionIdx, // 绘画id
    "prompt": msgTextEn || msgText, //图像生成描述文本
    add_new_data: JSON.stringify({
      text: msgText
    })
  }

  //image_ChatGPT_NEW_API_product
  // const chatData = {
  //   "model": userStore.modelType,
  //   image_urls: _data.fileList.map((item) => {
  //     return item.url
  //   }),
  //   "stream": false,
  //   "conversation_id": _data.sessionIdx, // 绘画id
  //   "prompt": msgText, //图像生成描述文本
  // }
  const msgData = {
    "text": msgText, //豆包 图像生成描述文本
    "prompt": msgTextEn || msgText, //图像生成描述文本
    "description": msgTextEn || msgText, //图像生成描述文本
    "image_urls": _data.fileList.map((item) => {
      return item.url
    }),
    add_new_data: JSON.stringify({
      text: msgText
    }),
    "user_id": userStore.userinfo.userId,
    "conversation_id": _data.sessionIdx, // 绘画id
    "stream": false
  }
  const resolutionRow = resolutionList.filter(item => item.value === chatStore.resolutionType)[0]

  const imageInfo = {
    quantity: chatStore.generatorType,
    width: resolutionRow.width,
    height: resolutionRow.height,
  }
  _data.scrollHeight = -1
  _data.isScroll = true
  let res = null
  try {
    if (_modelType === 'gemini') {
      res = await postGemini({...msgData, ...geminiData})
    } else  if (_modelType === 'gpt-4o-image') {
      res = await postChatGPT({size: resolutionRow.gptSize, ...chatData})
    }  else if (_data.fileList.length>0) {//奇画、flex图生图
      res = await postFluxKonTextCombined({
        prompt:  msgText,
        "image_paths": _data.fileList.map((item) => {
          return item.url
        }),
        "conversation_id": _data.sessionIdx, // 绘画id
        aspect_ratio:chatStore.resolutionType,
        "stream": false
      }, _modelType)
    } else {
      if (_modelType === 'flex') res = await postCombined({...msgData, ...imageInfo})
      if (_modelType === 'qiHua') res = await postVolcengine({...msgData, ...imageInfo})
    }
    if (res && res.data) {
      _data.msgText = '';
      _data.fileList = []
      getChatList()
    }
    showModel.value =false
    _data.gptThinking = false;
  } catch (err) {
    showModel.value =false
    _data.gptThinking = false;
  }
}

// timer.value = setInterval(() => {
//   if (_data.sessionIdx !== -1) getChatList()
// }, 60 * 1000)

// 设置滚动高度
function setScrollTop() {
  setTimeout(() => {
    if (msgListRef.value) msgListRef.value.scrollTop = _data.scrollHeight === -1 ? msgListRef.value.scrollHeight : _data.scrollHeight;
    _data.isScroll = false
  }, 50);
}

const previewFile = file => {
  if (file.size > 3 * 1024 * 1024) {
    //message.error('上传的文件大小不能超过3M')
    compressFile(file, (newFile) => {
      uploadImage(newFile)
    })
  } else {
    uploadImage(file)
  }
  return false
};
const uploadImage = async (file) => {
  const fileData = new FormData();
  fileData.append('image', file)
  fileData.append('method', '1')
  fileData.append('description', '1')
  fileData.append('related_id', '1')
  fileData.append('user_id', userStore.userinfo.userId)


  let fileId = Symbol("fileId")
  _data.fileList.push({
    id: fileId,
    loading: 1,
    url: ''
  })
  uploadImg(fileData).then(result => {
    const index = _data.fileList.findIndex(item => item.id === fileId)
    _data.fileList[index] = {
      loading: 0,
      size: file.size,
      name: file.name,
      url: result.data.image_url
    }
  }, err => {
    const index = _data.fileList.findIndex(item => item.id === fileId)
    _data.fileList[index] = {
      loading: -1,
      file: file
    }
  })
};

const retryFile = (file, index) => {
  _data.fileList.splice(index, 1);
  previewFile(file)
}
const delFileList = (index) => {
  _data.fileList.splice(index, 1);
}
//查看算力
const searchPoints = () => {
  getUserSeek({
    user_id: userStore.userinfo.userId
  }).then((res) => {
    userStore.setPoints(res.data.points)
    userStore.setVipInfo(res.data.vip_info)
  })
}
const openExampleModal = (item) => {
  exampleModalRef.value.open(item)
}
</script>

<style lang="less" scoped>
.home-wp {
  height: 100%;
  display: flex;

  .center {
    position: relative;
    width: 0;
    flex: 1;
    background-color: @bg-page-color;
    padding: 10px;
    display: flex;
    flex-direction: column;

    .select-model {
      position: absolute;
      top: 26px;
      left: 27px;
      z-index: 9;
    }

    .list {
      flex: 1;
      height: 0;
      // background: @bg-page-two-color;
      background: rgb(25, 25, 27);
      border-radius: 8px 8px 0 0;
      overflow: auto;
      padding: 10px 0 0;

      &::-webkit-scrollbar {
        display: block;
      }

      .item {
        padding: 0 20px;
        // border-bottom: 1px solid #262626;

        &:first-child {
          margin-top: 60px;
        }

        .ct {
          position: relative;
          margin: 0 auto;
          max-width: 100%;
          width: 100%;
          padding: 0 0 10px;
          font-size: 16px;
          line-height: 28px;

          .msg {
            min-height: 28px;
            word-break: break-word;
            color: #ffffff;

            .prompt {
              padding: 5px 0;

              img {
                width: 30px;
                height: 30px;
              }

              .model_used {
                margin: 0 10px;
                background-color: @bg-page-color;
                font-size: 15px;
                padding: 0 20px;
                color: #D3D3D3;
                border-radius: 20px;
              }

              .model_time {
                color: #505050;
              }
            }

            .thinkingIcon {
              background-color: @bg-page-color;
              text-align: center;
              border-radius: 4px;
              margin-bottom: 20px;
              padding: 150px 50px;
              width: 100%;
              max-width: 400px;
            }

            .error-tip {
              background-color: @bg-page-color;
              text-align: center;
              border-radius: 4px;
              margin-bottom: 20px;
              padding: 10px 50px;
              width: 300px;
              max-width: 100%;

              :deep(.ant-result-icon) {
                margin-bottom: 10px;
              }

              :deep(.ant-result-error .ant-result-icon > .anticon) {
                font-size: 50px;
                color: rgba(255, 255, 255, 0.45);
              }
            }

            .footer-setting {
              font-size: 15px;
              color: #623a9c;
              .footer-setting-btn{
                position: relative;
                cursor: pointer;
                font-size: 15px;
                color: #623a9c;
                padding-right: 10px;
                margin-right: 10px;
                &:hover{
                  color: #835bba;
                }
                &:after{
                  content: '';
                  display: block;
                  position: absolute;
                  height: 14px;
                  width: 1px;
                  top: calc(50% - 7px);
                  right: 0;
                  background: #623a9c;
                }
                &:last-child{
                  padding: 0;
                  margin: 0;
                  &:after{
                    display: none;
                  }
                }
              }
            }
          }

          .image-box {
            .img-list {
              .img {
                display: inline-block;
                margin-right: 10px;
                //height: 480px;
                cursor: pointer;
                border-radius: 8px;
                // padding: 10px;
                //  background-color: @bg-page-color;
              }
            }

            .img-tip {
              margin: 10px 0;
              color: #4C4C4C;
              line-height: 20px;
              font-size: 12px;
              padding: 0 5px 0 10px;
              border-left: 1px solid #4C4C4C;
            }

            .welcome-tip {
              margin: 10px 0 10px 40px;
              color: #A0A0A0;
              line-height: 20px;
              font-size: 12px;
              padding: 0 5px;

              span {
                color: #FFFFFF;
              }
            }

            .operate-tip {
              margin: 10px 0 10px 40px;

              .operate-tip-item {
                cursor: pointer;
                display: inline-block;
                font-size: 12px;
                padding: 0 10px;
                margin: 0 5px 5px 0;
                border: 1px solid #4C4C4C;
                border-radius: 16px;
              }
            }
          }
        }

        &.myself {
          .ct {
            padding: 60px 0 0;
          }

          .head {
            left: inherit;
            background: initial;
            color: #fff;
            font-size: 14px;
            line-height: 30px;
          }

          .msg {
            width: 80%;
            margin-left: 20%;
            text-align: right;

            .prompt {
              display: inline-block;
              font-size: 13px;
              padding: 5px 10px;
              background-color: @bg-page-two-color;
              border-radius: 8px;
              text-align: left;
            }
            .edt-prompt{
              display: block;
              width: 100%;
              position: relative;
              border: 1px solid #0e7cb3;
              &:hover{
                border: 1px solid #00A9FE;
              }
              .send-btn {
                margin-left: 5px;
                font-size: 14px;
                cursor: pointer;
                color: #fff;
                border: 0;
                background: @btn-bg-two-color;
                &:hover{
                  opacity: 0.8;
                }
                .iconfont {
                  fill: #FFFFFF;
                  font-size: 14px;
                  margin-right: 5px
                }
              }
            }
            .footer-setting {
               font-size: 15px;
              color: #623a9c;
              .del-btn{
                cursor: pointer;
                font-size: 15px;
                color: #623a9c;
                &:hover{
                  color: #835bba;
                }
              }
            }
          }

          .img-list {
            &:after {
              content: '';
              display: block;
              clear: both;
            }

            text-align: right;

            .img {
              display: inline-block;
              margin-left: 5px;
              //height: 320px;
              border-radius: 8px;
              cursor: pointer;
            }
          }
        }
      }
    }

    .bottom {
      padding: 20px 20px;
      // background: @bg-page-two-color;
      background:rgb(25, 25, 27);
      // background: @bg-page-two-color;
      border-radius: 0 0 8px 8px;
      position: relative;

      &.has-file {
        padding: 70px 20px 20px;
      }

      .send-box {
        max-width: 100%;
        width: 100%;
        border: 1px solid #212C69;
        box-shadow: 0 0 10px rgba(0, 0, 0, .1);
        display: flex;
        align-items: center;
        border-radius: 40px;
        background-color: @bg-page-color;

        &:hover, &.over {
          border-color: #374ed3;
        }

        .ipt-box {
          color: #fff;
          position: relative;
          width: 100%;
          padding: 10px 15px 10px 50px;

          .ipt {
            width: 100%;
            color: #FFFFFF;
            font-size: 14px;
          }

          .up-file-list {
            position: absolute;
            top: -70px;
            left: 0;
            z-index: 99;

            & > div {
              margin-right: 15px;
              border: 1px solid #4A4A4B;
              padding: 5px 15px;
              border-radius: 5px;
              position: relative;

              .loading-tips {
                font-size: 14px;
                color: #939393;
                line-height: 25px;
                cursor: pointer;

                :deep(.ant-btn-link) {
                  font-size: 14px !important;
                  height: 24px !important;
                  line-height: 24px !important;
                }
              }

              img {
                width: 50px;
                height: 50px;
                border-radius: 5px;
              }

              .img-info {
                padding: 5px 10px;
                color: #939393;
                font-size: 14px;
                line-height: 20px;
                margin-left: 5px;

                .line1 {
                  max-width: 160px;
                }
              }
            }

            .close-icon {
              cursor: pointer;
              font-size: 24px;
              color: #4A4A4B;
              background-color: @bg-page-color;
              border-radius: 50%;
              position: absolute;
              top: -10px;
              right: -10px;
            }
          }

          .btn-list {
            //position: absolute;
            //bottom: 13px;
            //z-index: 2;
            //right: 20px;
            //width: 210px;
            .send-btn {
              margin-left: 5px;
              display: flex;
              font-size: 14px;
              cursor: pointer;
              color: #fff;
              border: 0;
              background: @btn-bg-two-color;
              &:hover{
                opacity: 0.8;
              }
              .iconfont {
                fill: #FFFFFF;
                font-size: 14px;
                margin-right: 5px
              }
            }
          }

          .upload-box {
            position: absolute;
            top: calc(50% - 16px);
            z-index: 2;
            left: 5px;

            font-size: 16px;
            cursor: pointer;

            :deep(.ant-upload) {
              padding: 0 5px;
            }

            :deep(.ant-btn) {
              background-color: inherit;
              color: #797979;
              border-color: #2A2A2A
            }
          }
        }
      }

      .msg-tips {
        color: #666666;
        font-size: 12px;
        line-height: 14px;
        position: absolute;
        bottom: 0;
        left: 30px;
        right: 30px;
        text-align: center;
      }
    }
  }
}
</style>
<template>
  <div class="head">
    <div class="flex suspension-box">
      <div class="flex-1 flex left items-center justify-start">
        <div class="left-logo flex justify-center">
          <img src="../../assets/image/logo-beat.svg" alt="">
<!--          <img src="../../assets/image/menu_logo.svg" alt="">-->
        </div>
<!--        <div class="temporary-title flex items-end">南康家具AI综合服务平台</div>-->
      </div>
      <div class="flex right items-center justify-center" v-if="userStore&&userStore.token">
<!--        <div class="other-box flex items-center justify-center" @click="toShare">-->
<!--          <i class="iconfont icon-fenxiang1"></i>分享-->
<!--        </div>-->
        <div class="other-box power flex items-center justify-center" @click="showVipModal('power')">
         算力充值
        </div>
        <div class="other-box vip flex items-center justify-center" @click="showVipModal('vip')">
           升级会员
        </div>
        <div class="other-box flex items-center justify-center" @click="toUsingTutorials">
          <i class="iconfont icon-xingzhuang"></i>使用教程
        </div>
        <div class="icon-box flex items-center justify-center">
          <i class="iconfont icon-jifen"></i>{{  userStore.points }}算力
        </div>
        <div class="suspension-text" @click="showVipModal('vip')" v-if="!userStore.vipInfo||!userStore.vipInfo.level">
          开通会员领取更多算力
        </div>
        <a-avatar :size="32" class="vip-icon"  v-if="userStore.vipInfo&&userStore.vipInfo.level">
          <template #icon> <i class="iconfont icon-huangguan"></i> </template>
        </a-avatar>
        <a-avatar :size="32" class="avatar-icon" @click="showUserInfo">
          <template #icon><UserOutlined /></template>
        </a-avatar>
      </div>
      <div class="flex right items-center justify-center" v-if="!userStore|| !userStore.token">
        <div class="login-btn" @click="showLoginModal">
          登录
        </div>
      </div>
    </div>
    <loginModal v-if="userStore.showLogin"></loginModal>
    <userInfoModal ref="userInfoModalRef"></userInfoModal>
<!--    <vipModal ref="vipModalRef" @change="toPionts"></vipModal>-->
<!--    <pointsModal ref="pointsModalRef"></pointsModal>-->
    <ShareModel ref="shareModelRef"></ShareModel>
    <vipOrPointsModal ref="vipOrPointsModalRef"></vipOrPointsModal>
    <VideoTutorial ref="videoTutorialRef"></VideoTutorial>
  </div>
</template>

<script setup>
import {onMounted, onUnmounted, ref, watch} from 'vue'
import { UserOutlined } from '@ant-design/icons-vue';
import loginModal from "./../user/loginModal.vue";
import userInfoModal from "@/components/modules/userTools/userModal.vue";
// import vipModal from "@/components/modules/userTools/vipModal.vue";
// import pointsModal from "@/components/modules/userTools/pointsModal.vue";
import vipOrPointsModal from "@/components/modules/userTools/vipOrPointsModal.vue";
import {useUserStore} from '@/store/userStore';
import {getUserSeek} from "@/api/pay.js";
import ShareModel from "@/components/shareModel/index.vue";
import VideoTutorial from "@/components/videoTutorial/index.vue";
import emitter from "@/utils/emitter.js";
import {useRoute, useRouter} from "vue-router";
const router = new useRouter();
const route = useRoute()
const userStore = useUserStore();
const userInfoModalRef = ref();
const videoTutorialRef = ref();
// const vipModalRef = ref();
// const pointsModalRef = ref();
const shareModelRef = ref()
const vipOrPointsModalRef = ref()
watch(() => userStore.token, (token) => {
  if(token) searchPoints()
});
// 显示我的账户
function showUserInfo() {
  userInfoModalRef.value.open();
}
function showVipModal(type='vip') {
  if(route.path === '/recharge'){
    router.replace({
      path: '/recharge',
      query: {
        type: type
      }
    })
  } else {
    router.push({
      path: '/recharge',
      query: {
        type: type
      }
    })
  }
 // vipOrPointsModalRef.value.open();
   // vipModalRef.value.open();
}
function showLoginModal() {
  userStore.setShowLogin(true);
}
const showVideoTutorial = (e) => {
  console.log(e);
  videoTutorialRef.value.open();
}
onMounted(() => {
  emitter.on('refresh-user', searchPoints);
  emitter.on('video-tutorial', showVideoTutorial);
  emitter.on('show-vip-modal', showVipModal);
})

onUnmounted(() => {
  emitter.off('refresh-user')
  emitter.off('video-tutorial');
  emitter.off('show-vip-modal');
})
//
// function showPointsModalRef() {
//   vipOrPointsModalRef.value.open();
//   //pointsModalRef.value.open();
// }
//
function toUsingTutorials() {
  window.open('https://g070zosrd54.feishu.cn/wiki/BydewxOG6iG35HkVkZQcgijBntd?fromScene=spaceOverview','_blank');
}
//查看算力
const searchPoints = () =>{
  if(!userStore.userinfo|| !userStore.userinfo.userId) return
  getUserSeek({
    user_id:userStore.userinfo.userId
  }).then((res) => {
    userStore.setVipInfo(res.data.vip_info)
    userStore.setPoints(res.data.points)
  })
}
if( userStore.token) searchPoints()
const open = (type) =>{
  showVipModal()
}
defineExpose({
  open
})

</script>

<style lang="less" scoped>
.suspension-box {
  position: fixed;
  top: 0;
  right: 0;
  left: 0;
  height: 50px;
  text-align: center;
  background-color: @bg-page-color;
  border-bottom: 1px solid #292929;
  z-index: 9;
  .left{
    margin-left: 20px;
    .left-logo {
      //font-weight: 500;
      //font-size: 18px;
      //color: #FFFFFF;
      img{
        height: 36px;
      }
    }
    .temporary-title{
      height: 36px;
      padding: 0;
      color: #4D6BFE;
      font-size: 18px;
    }
  }
  .right{
    margin-right: 20px;
    .icon-box{
      padding: 0 15px;
      color: #B17DFE;
      border: 1px solid #422F55;
      border-radius: 20px;
      height: 30px;
      min-width: 130px;
      line-height: 30px;
      margin-right: 10px;
      cursor: pointer;
      .iconfont{
        font-size: 20px;
      }
    }
    .other-box{
      padding: 0 15px;
      color: #A2A2A2;
      border: 1px solid #373737;
      border-radius: 20px;
      height: 30px;
      line-height: 30px;
      margin-right: 10px;
      cursor: pointer;
      .iconfont{
        font-size: 20px;
      }
      &.vip{
        border: 1px solid #FFAA06;
        color: #FFAA06;
      }
    }
    .suspension-text{
      width: 200px;
      height: 30px;
      line-height: 30px;
      border-radius: 15px;
      color: #FFFFFF;
      margin-right: 10px;
      cursor: pointer;
      //  background: #3253FE;
      background: @btn-bg-color;
    }
    .login-btn{
      width: 120px;
      height: 30px;
      line-height: 30px;
      border-radius: 15px;
      color: #FFFFFF;
      margin-right: 10px;
      cursor: pointer;
      //  background: #3253FE;
      background: @btn-bg-color;
    }
    .avatar-icon{
      cursor: pointer;
    }
    .vip-icon{
      cursor: pointer;
      margin-right: 10px;
      background:#FFAA06 ;
      .iconfont{
        color:#FFFFFF;
      }
    }
  }
}
</style>
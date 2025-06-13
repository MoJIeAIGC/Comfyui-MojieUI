<template>
  <a-modal class="user-modal" v-model:visible="_data.visible" :maskClosable="false" :footer="null" width="580px">
    <div slot="title"></div>
    <div class="member-content">
      <div class="header flex">
        <div class="user-info flex-1 flex justify-start items-center">
          <a-avatar :size="48" class="avatar-icon">
            <template #icon>
              <UserOutlined/>
            </template>
          </a-avatar>
          <div>
            {{ _data.info.phone||_data.info.username }}
          </div>
        </div>
        <div class="points-box flex-1 flex justify-end items-center">
          <div class="icon-box flex justify-center items-center">    <i class="iconfont icon-jifen"></i>{{  userStore.points }}算力</div>
        </div>
      </div>
      <div class="user-info-list">
        <div class="flex user-info-item" v-for="item in dataSource">
            <div class="flex-1">{{item.name}}</div>
            <div>{{item.key === 'points'?  userStore.points: item.key === 'vip'? getVip : item.info}}</div>
        </div>
        <div class="login-out text-center bt" @click="updatePassword">修改密码</div>
        <div class="login-out text-center" @click="loginOut">退出登录</div>
      </div>
    </div>
  </a-modal>
  <updatePwdModal ref="updatePwdModalRef"></updatePwdModal>
</template>

<script setup>
import {computed, reactive, ref} from 'vue'
import {UserOutlined} from '@ant-design/icons-vue';
import {useUserStore} from '@/store/userStore.js';
import dayjs from 'dayjs';
import {Modal} from "ant-design-vue";
import {getUserSeek} from "@/api/pay.js";
import updatePwdModal from "@/components/modules/userTools/updatePwdModal.vue";
import {queryUserShareCode} from "@/api/login.js";
import {useOrderStore} from "@/store/orderStore.js";
const userStore = useUserStore();
const updatePwdModalRef = ref();
const userInfo =ref({})
const _data = reactive({
  visible: false,
  info: userStore.userinfo ? userStore.userinfo : {},
  newInfo:{}
})

const dataSource = ref( [
  {
    key: 'name',
    name: '账号',
    info: _data.info.phone||_data.info.username,
  },
  {
    key: 'points',
    name: '算力',
    info: ''
  },
  {
    key: 'vip',
    name: '会员有效期',
    info: ''
  },
  {
    key: 'shareCode',
    name: '我的邀请码',
    info:  ''
  }
])
const getVip = computed(() => {
  if(userInfo.value.vip_info) {
    if(!userInfo.value.vip_info.end_time) return ''
    return dayjs(userInfo.value.vip_info.end_time).format('YYYY-MM-DD HH:mm:ss')
  }
  return ''
});
const getCode = () => {
  queryUserShareCode().then(res => {
    dataSource.value[3].info = res.data.share_code
  })
}
function open() {
  _data.visible = true;
  searchPoints()
  getCode()
}
function updatePassword() {
  updatePwdModalRef.value.open()
}
function loginOut() {
  Modal.confirm({
    title: '提示',
    content: '请确认是否登出？',
    okText: '确定',
    cancelText: '取消',
    onOk() {
      useOrderStore().setOrderInfo({})
      userStore.logout();
      _data.visible = false
    },
  });
}
//查看算力
const searchPoints = () =>{
  getUserSeek({
    user_id:userStore.userinfo.userId
  }).then((res) => {
     userStore.setPoints(res.data.points)
     userStore.setVipInfo(res.data.vip_info)
     userInfo.value = res.data
  })
}
defineExpose({
  open
})

</script>

<style lang="less" scoped>
.member-content {
  .header {
    padding: 50px;
    .user-info {
      .avatar-icon {
        margin-right: 10px;
      }
    }
    .points-box{
      .icon-box {
        padding: 8px 10px;
        color: #65C1FF;
        border: 1px solid #65C1FF;
        border-radius: 20px;
        height: 30px;
        line-height: 30px;
        .icon-jifen{
          margin-right: 5px;
          font-size: 24px;
          color: #00A9FE;
        }
      }
    }
  }
  .user-info-list{
    background: @bg-page-two-color;
    .user-info-item{
      padding: 16px 30px;
      border-bottom: 1px solid #3B3C41;
      cursor:pointer;
      &:hover{
        background: #4a4c57;
      }
    }
    :deep(.ant-table-cell){
      background: #2C2D33;
      color: #ffffff;
      padding: 16px 30px;
      border-bottom: 1px solid #3B3C41;
    }
    :deep(.ant-table-row:hover .ant-table-cell){
      background: #4a4c57;
    }
    .login-out{
      padding: 16px 30px;
      cursor:pointer;
      &.bt{
        border-bottom:1px solid #3B3C41;
      }
      &:hover{
        background: #4a4c57;
      }
    }
  }
}
</style>
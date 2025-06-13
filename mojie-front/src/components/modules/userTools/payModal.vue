<template>
  <a-modal class="vip-modal" v-model:visible="_data.visible" @cancel="cancel" :maskClosable="false" :footer="null"
           width="340px">
    <div slot="title"></div>
    <a-spin tip="加载中..." :spinning="_data.loading">
    <div class="member-content">
        <div class="pay-code" v-if="_data.orderDetails&&_data.orderDetails.code_url">
          <div class="pay-price text-center">支付<span>{{ _data.checkInfo.price }}</span>元{{
              _data.checkInfo.method === 'pp' ? '购买算力' : '开通会员'
            }}</div>
          <div class="pay-img">
            <qrcode-vue :value="_data.orderDetails.code_url" :margin="1" :image-settings="_data.imageSettings" :size="250" level="H"></qrcode-vue>
          </div>
          <div class="pay-info flex justify-center items-center">
            <div>
              <div class="pay-price-tips text-center">请使用微信扫码支付 </div>
              <a-button type="primary" class="pay-price-btn items-center justify-center" @click="pey">
                <template #icon><i class="iconfont icon-zhifubaozhifu"></i>&nbsp;</template>
                使用支付宝支付
              </a-button>
            </div>
          </div>
          <div class="footer-tips text-center">扫码支付，表示您已阅读并接受  <a-button class="link-btn" size="small" type="link" @click.stop="openPage('user')">《服务协议》</a-button> </div>
        </div>
    </div>
    </a-spin>
  </a-modal>
</template>

<script setup>
import { defineEmits, onUnmounted, reactive} from 'vue'
import {message, Modal} from "ant-design-vue";
import {useOrderStore} from '@/store/orderStore.js';
import {payProduct, getPayWechat, getOrderDetails, getUserSeek} from "@/api/pay.js";
import QrcodeVue from 'qrcode.vue';
import {useUserStore} from "@/store/userStore.js";
import dayjs from "dayjs";
import logo from "@/assets/image/logo.png";

const userStore = useUserStore();
const orderStore = useOrderStore();
const emit = defineEmits(['change']);
const _data = reactive({
  visible: false,
  loading: false,
  orderDetails: {},
  checkInfo: {},
  payUrl: '',
  timer: null,
  imageSettings:{
    src: logo,
    width: 52,
    height: 52,
    excavate: true
  }
})
onUnmounted(() => {
  if (_data.timer) clearTimeout(_data.timer)
})
const searchPoints = (type) => {
  getUserSeek({
    user_id: userStore.userinfo.userId
  }).then((res) => {
    userStore.setPoints(res.data.points)
    userStore.setVipInfo(res.data.vip_info)
    if(type==='success') showTipConfirm()
  })
}
const payOrder = () => {
  _data.loading = true
  let orderInfo = orderStore.orderInfo || {}
  if(orderInfo[_data.checkInfo.id]){
      const timeData = orderInfo[_data.checkInfo.id].time - new Date().getTime()
      if(timeData > 0) {
        _data.orderDetails = orderInfo[_data.checkInfo.id].res
        getOrderInfo()
        _data.loading = false
        return
      }
  }
  getPayWechat({
    product_id: _data.checkInfo.id
  }).then(res => {
      orderInfo[_data.checkInfo.id] = {
        time: new Date().getTime() + 60*1000 *6,
        res: res.data
      }
     orderStore.setOrderInfo(orderInfo)
    _data.orderDetails = res.data
    getOrderInfo()
  }).finally(() => {
    _data.loading = false
  })
}
const openPage = (type) => {
  window.open('/protocolPolicy?type=' + type, '_blank');
}
const getOrderInfo = () => {
  getOrderDetails({
    order_id: _data.orderDetails.orderid
    //order_id: '79544157770818897522764051062528'
  }).then(res => {
    // 201 未支付
    // 200 已经支付
    let orderInfo = orderStore.orderInfo || {}
    if(orderInfo[_data.checkInfo.id]){
      const timeData = orderInfo[_data.checkInfo.id].time - new Date().getTime()
      if(timeData < 0) {
        orderInfo[_data.checkInfo.id] = null
        orderStore.setOrderInfo(orderInfo)
        if (_data.timer) clearTimeout(_data.timer)
        payOrder()
        return
      }
    }
    if (res.data && res.data.new_points) {
      message.info('支付成功')
      // _data.visible = false
      orderInfo[_data.checkInfo.id] = null
      orderStore.setOrderInfo(orderInfo)
      // payOrder()
      searchPoints('success')
      if (_data.timer) clearTimeout(_data.timer)
    } else {
      if (_data.timer) clearTimeout(_data.timer)
      _data.timer = setTimeout(() => {
        getOrderInfo()
      }, 5 * 1000)
    }
  })
}
const showTipConfirm = () => {
  let vipDate = ''
  if (userStore.vipInfo&&userStore.vipInfo.end_time) vipDate =  dayjs(userStore.vipInfo.end_time).format('YYYY-MM-DD HH:mm:ss')
  const _Modal = Modal.confirm({
    closable: true,
    maskClosable: true,
    centered: true,
    title: _data.checkInfo.method ==='pp' ? '购买算力成功' : '购买会员成功！',
    content: userStore.vipInfo ? '您的会员有效期至: '+vipDate+ ' ,   算力：' +userStore.points : '您当前算力: '+userStore.points,
    okText: '继续购买',
    okType: 'danger',
    class: 'tips-modal',
    cancelText: '取消',
    width: '500px',
    onOk() {
      payOrder()
    },
    onCancel() {
      _Modal.destroy();
      _data.visible = false;
    },
  });
};


function open(item) {
  if (_data.timer) clearTimeout(_data.timer)
  _data.checkInfo = item
  payOrder()
  _data.visible = true;
}


const cancel = () => {
  if (_data.timer) clearTimeout(_data.timer)
}
const pey = () => {
  // message.info('功能开发中')
  payProduct({
    product_id: _data.checkInfo.id, //	商品ID
    payment_method: 1, //支付方式(1:支付宝 2:微信支付 3:银行卡)
  }).then(res => {
    //_data.payUrl = res.data.payment_url
    // window.open(res.data.payment_url, '_blank' )
   openNewPage(res.data.payment_url)
  })
}
const openNewPage = (url) => {
  let w = screen.availWidth - 200, h = screen.availHeight - 160
  if (w < 400) w = 400
  if (h < 200) h = 200
  window.open(url, '', 'left=100,top=50,height=' + h + ',width=' + w + ',scrollbars=yes,status=yes,location=no,toolbar=no,menubar=no,resizable=yes')
}
defineExpose({
  open
})

</script>

<style lang="less" scoped>
.member-content {
   min-height: 340px;
  .pay-code {
    border-radius: 12px;
    margin:0 15px;
    background: @bg-page-color;

    .pay-img {
      margin: 10px 0;
      height: 260px;
      padding: 5px;
      background: #FFFFFF;
      border-radius: 8px;
    }
    .pay-price {
      font-size: 16px;

      span {
        margin-left: 5px;
        font-size: 24px;
        color: #2b86ff;
      }
    }
    .pay-info {

      .pay-price-tips {
        padding: 5px 0;
        color: #FFFFFF;
        font-size: 12px;
        border-radius: 20px;
      }

      .pay-price-btn {
        display: flex !important;
        color: #FFFFFF;
        font-size: 12px;
        border-radius: 20px;

        .iconfont {
          font-size: 16px;
          line-height: 16px;
        }

        :deep(>span) {
          margin: 0 !important;
        }
      }
    }
    .footer-tips{
      margin-top: 10px;
      padding: 5px 0;
      color: #535A6B;
      font-size: 12px;
      border-radius: 20px;
      .link-btn{
        font-size: 12px;
        padding: 0;
      }
    }
  }
}
</style>
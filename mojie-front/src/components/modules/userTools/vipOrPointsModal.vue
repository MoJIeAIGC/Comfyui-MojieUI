<template>
  <a-modal class="vip-modal" v-model:visible="_data.visible" @cancel="cancel" :maskClosable="false" :footer="null"
           width="800px">
    <div slot="title"></div>
    <div class="member-content">
      <a-spin tip="加载中..." :spinning="_data.loading">
        <div class="header flex">
          <div class="user-info flex justify-start items-center">
            <a-avatar :size="40" class="avatar-icon">
              <template #icon>
                <UserOutlined/>
              </template>
            </a-avatar>
            <div>
              {{ userStore.userinfo.phone || userStore.userinfo.username }}
            </div>
            <a-avatar :size="24" class="vip-icon" :class="{vip: userStore.vipInfo&&userStore.vipInfo.level}">
              <template #icon><i class="iconfont icon-huangguan"></i></template>
            </a-avatar>
            <div class="icon-box flex justify-center items-center">
              <i class="iconfont icon-jifen"></i>{{ userStore.points }}算力
            </div>
          </div>
          <div class="flex-1 flex justify-end items-center">
            <div class="vip-data" v-if="userStore.vipInfo&&userStore.vipInfo.level">会员有效期：{{ getVip }}</div>
          </div>
        </div>
        <div class="title text-center">
          <div class="h5">开通奇画会员 解锁更多能力</div>
          <div class="tips">选择合适你的套餐，或直接购买算力</div>
        </div>
        <div class="member-list">
          <div class="member-list-item" v-for="item in _data.list" :key="item.id"
               :class="{active:_data.checkInfo.id === item.id,'col-4':_data.list.length===4}"
               @click="chooseProduct(item,'vip')">
            <div class="list-title">{{ item.description }}</div>
            <div class="list-count"><i class="iconfont icon-renmingbi"></i><span>{{ item.price }}</span></div>
            <div class="list-subheading">赠送{{ item.points }}算力</div>
          </div>
        </div>

        <!--      <div class="text-list flex">-->
        <!--        <div class="text-item flex-1 text-center" v-for="cItem in _data.contentList" :key="cItem.title">-->
        <!--          <CheckOutlined/>-->
        <!--          {{ cItem.title }}-->
        <!--        </div>-->
        <!--      </div>-->
        <div class="title-points-h5 text-center">
          <div>购买算力</div>
        </div>
        <div class="content-box">
          <div class="product-box">
            <div class="points-list">
              <div class="points-list-item" v-for="(item,index) in _data.pointLlist" :key="item.id" :class="{active:_data.checkInfo.id === item.id}" @click="chooseProduct(item,'points')">
                <div class="list-title text-center flex justify-center items-center"><i class="iconfont icon-jifen"></i>{{ item.points}}</div>
                <div class="list-count text-center flex justify-center items-center">
                  <i class="iconfont icon-renmingbi"></i>{{ item.price }}
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="pay-code flex" v-if="_data.orderDetails&&_data.orderDetails.code_url">
          <div class="pay-img">
            <qrcode-vue :value="_data.orderDetails.code_url" :size="120" level="H"></qrcode-vue>
          </div>
          <div class="pay-info flex justify-center items-center">
            <div>
              <div class="pay-price">实付<span>{{ _data.checkInfo.price }}</span></div>
              <div class="pay-price-tips">使用微信扫码支付{{
                  _data.checkInfo.method === 'pp' ? '充值算力' : '开通会员'
                }}
              </div>
              <a-button type="primary" class="pay-price-btn items-center justify-center" @click="pey">
                <template #icon><i class="iconfont icon-zhifubaozhifu"></i>&nbsp;</template>
                使用支付宝支付
              </a-button>
            </div>
          </div>
        </div>
      </a-spin>
    </div>
  </a-modal>
</template>

<script setup>
import {computed, defineEmits, onUnmounted, reactive} from 'vue'
import { UserOutlined} from '@ant-design/icons-vue';
import {message, Modal} from "ant-design-vue";
import {useOrderStore} from '@/store/orderStore.js';
import {payProduct, getProList, getPayWechat, getOrderDetails, getUserSeek} from "@/api/pay.js";
import QrcodeVue from 'qrcode.vue';
import {useUserStore} from "@/store/userStore.js";
import dayjs from "dayjs";

const userStore = useUserStore();
const orderStore = useOrderStore();
const emit = defineEmits(['change']);
const _data = reactive({
  visible: false,
  loading: false,
  orderDetails: {},
  checkInfo: {},
  payUrl: '',
  list: [],
  contentList: [
    // {title: '每日赠送算力100'},
    {title: '持续更新新内容'},
    // {title: '购买算力享75折优惠'},
    {title: '线路优先对话'}
  ],
  timer: null
})
onUnmounted(() => {
  if (_data.timer) clearTimeout(_data.timer)
})
const initList = () => {
  _data.loading = true
  getProList({
    method: 'vip'
  }).then(res => {
    _data.list = res.data
    _data.checkInfo = res.data[0]
    initListPoints()
    payOrder()
  })
}
const initListPoints = () => {
  getProList({method: 'pp'}).then(res => {
    _data.pointLlist = res.data
  })
}
const getVip = computed(() => {
  if (userStore.vipInfo) {
    if (!userStore.vipInfo.end_time) return ''
    return dayjs(userStore.vipInfo.end_time).format('YYYY-MM-DD HH:mm:ss')
  }
  return ''
});
const searchPoints = (type) => {
  getUserSeek({
    user_id: userStore.userinfo.userId
  }).then((res) => {
    userStore.setPoints(res.data.points)
    userStore.setVipInfo(res.data.vip_info)
    // showTipConfirm()
    if(type==='success') showTipConfirm()
  })
}
const payOrder = () => {
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

const chooseProduct = (item) => {
  if (_data.checkInfo.id === item.id) return
  if (_data.timer) clearTimeout(_data.timer)
  _data.checkInfo = item
  payOrder()
  //pey()
}

function open() {
  if (_data.timer) clearTimeout(_data.timer)
  initList()
  searchPoints()
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
  padding: 20px 0 0;

  .header {
    padding: 0 0 15px;

    .user-info {
      .avatar-icon {
        margin-right: 5px;
      }
    }

    .vip-icon {
      cursor: pointer;
      margin-left: 10px;
      background: #6a6967;

      .iconfont {
        color: #434040;
      }

      &.vip {
        background: #FFAA06;

        .iconfont {
          color: #FFFFFF;
        }
      }
    }

    .vip-data {
      color: #999999;
    }
  }

  .title {
    .h5 {
      font-size: 32px;
      color: transparent;
      background-clip: text;
      background-image: linear-gradient(to right, #00D1FE, #008AFE, #00D1FE);
    }

    .tips {
      padding: 10px 0;
    }
  }

  .icon-box {
    padding: 0 15px;
    color: #B17DFE;
    border: 1px solid #422F55;
    border-radius: 20px;
    height: 30px;
    min-width: 130px;
    line-height: 30px;
    margin-left: 10px;
    cursor: pointer;

    .iconfont {
      font-size: 20px;
    }
  }

  .member-list {
    .member-list-item {
      cursor: pointer;
      background: @bg-page-two-color;
      display: inline-block;
      width: calc(33% - 16px);
      padding: 25px 15px;
      margin: 8px;
      border-radius: 12px;

      &.active {
        background: url("../../../assets/image/vip_01.png") no-repeat;
        background-size: 100% 100%;
        border: 2px solid rgba(0, 138, 254, 0.5);
      }

      &.col-4 {
        width: calc(25% - 16px);
      }

      .list-title {
        font-size: 20px;
        padding: 5px 0;
      }

      .list-count {
        font-size: 16px;

        span {
          font-size: 36px;
          padding: 0 0 0 5px;
        }
      }

      .list-subheading {
        font-size: 14px;
        color: #919293;
        line-height: 20px;
      }

      .list-btn {
        padding: 15px 0;

        :deep(.ant-btn-primary) {
          background: #35BBFF;
          color: #000000;
        }
      }
    }
  }

  .text-list {
    margin: 15px;
    background: @bg-page-color;
    border-radius: 12px;
    padding: 15px 10px;

    .text-item {
      color: #C8C9C9;
      line-height: 30px;
      border-right: 1px solid #4D5054;
      font-size: 14px;

      :deep(.anticon.anticon-check) {
        margin-right: 5px;
      }

      &:last-child {
        border-right: 0;
      }
    }
  }

  .title-points-h5 {
    padding: 15px 0 10px;

    > div {
      display: inline-block;
      position: relative;
      line-height: 30px;
      font-size: 20px;

      &:before, &:after {
        content: "";
        display: inline-block;
        position: absolute;
        height: 2px;
        width: 160px;
        top: 14px;
        background: linear-gradient(to right, #16171B, #5A5B5F);
      }

      &:before {
        left: -170px;
      }

      &:after {
        right: -170px;
        background: linear-gradient(to left, #16171B, #5A5B5F);
      }
    }
  }

  .product-box {
    .points-list {
      position: relative;

      .points-list-item {
        cursor: pointer;
        background: @bg-page-two-color;
        display: inline-block;
        width: calc(20% - 16px);
        padding: 15px;
        margin: 8px;
        border-radius: 5px;

        &.active {
          border: 1px rgba(78, 117, 175, 0.8) solid;
        }

        .list-title {
          height: 40px;
          font-size: 32px;

          .iconfont {
            color: #00B1FE;
            height: 40px;
            font-size: 28px;
          }
        }

        .list-count {
          color: #9a9898;
          font-size: 24px;

          .iconfont {
            height: 22px;
            font-size: 18px;
          }
        }
      }
    }

    .product-box-tips {
      margin-top: 40px;
      padding: 0 15px;
      color: #A5A7A9;
    }
  }

  .pay-code {
    border-radius: 12px;
    margin: 15px;
    background: @bg-page-color;
    padding: 15px 10px;

    .pay-img {
      padding: 10px;
      height: 140px;
      background: #FFFFFF;
      border-radius: 8px;
    }

    .pay-info {
      margin-left: 25px;

      .pay-price {
        font-size: 28px;

        span {
          margin-left: 5px;
          font-size: 48px;
          color: #2b86ff;
        }
      }

      .pay-price-tips {
        color: #919293;
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
  }
}

@media screen and (max-width: 900px) {
  .member-content {
    padding: 0;

    .title {
      .h5 {
        font-size: 24px;
      }
    }

    .member-list {
      .member-list-item {
        width: calc(50% - 10px);
        padding: 10px;
        margin: 5px;
        border-radius: 12px;

        .list-title {
          font-size: 18px;
          padding: 0;
        }

        .list-count {
          font-size: 12px;

          .iconfont {
            font-size: 12px;
          }

          span {
            font-size: 20px;
            padding: 0 10px;
          }
        }

        .list-subheading {
          display: none;
        }

        .list-btn {
          display: none;
        }
      }
    }

    .text-list {
      margin: 5px 0;
      display: block;

      .text-item {
        display: inline-block;
        width: calc(50% - 2px);
        color: #C8C9C9;
        margin: 0;
        line-height: 16px;
        border: 0;
        font-size: 12px;
        text-align: left;
      }
    }

    .pay-code {
      border-radius: 12px;
      margin: 10px;
      background: @bg-page-color;
      padding: 10px;

      .pay-img {
        img {
          height: 100px;
          width: 100px;
          border-radius: 4px;
        }
      }

      .pay-info {
        margin-left: 15px;

        .pay-price {
          font-size: 16px;

          span {
            margin-left: 5px;
            font-size: 28px;
          }
        }

        .pay-price-tips {
          color: #919293;
        }
      }
    }
  }
}
</style>
<template>
  <a-result
      status="success"
      title="支付成功!"
      :sub-title="subTitle"
    >
    <template #extra>
      <a-button key="console" type="primary" @click="close">关闭</a-button>
    </template>
  </a-result>
</template>
<script setup>
// import {useRoute} from "vue-router";
import {getUserSeek} from "@/api/pay.js";
import {useUserStore} from "@/store/userStore.js";
import {ref} from "vue";
import dayjs from "dayjs";

const userStore = useUserStore();
const subTitle =ref('');
// const route = useRoute()
const close = () => {
  window.opener = null;
  window.open('', '_self')
  window.close()
}
const searchPoints = (type) => {
  getUserSeek({
    user_id: userStore.userinfo.userId
  }).then((res) => {
    userStore.setPoints(res.data.points)
    userStore.setVipInfo(res.data.vip_info)
    let vipDate = ''
    if (userStore.vipInfo&&userStore.vipInfo.end_time) vipDate =  dayjs(userStore.vipInfo.end_time).format('YYYY-MM-DD HH:mm:ss')
    subTitle.value =  userStore.vipInfo ? '您的会员有效期至: '+vipDate+ ' ,   算力：' +userStore.points : '您当前算力: '+userStore.points
    window.opener.postMessage('refresh', '*');
  })
}
searchPoints()
// 'status': 'success',
//     'order_no': order.order_no,
//     'amount': str(order.actual_amount),
//     'payment_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
//     'product_name': order.product.description if order.product else '',
//     'trade_no': data.get('trade_no', '')  # 从同步通知获取交易号
</script>
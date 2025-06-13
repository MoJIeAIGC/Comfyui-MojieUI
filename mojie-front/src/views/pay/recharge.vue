<template>
  <div class="recharge-box flex justify-center">
    <div class="member-content">
      <a-spin tip="加载中..." :spinning="_data.loading">
        <div class="title text-center" v-if="payType==='vip'">
          <div class="h5">开通奇画会员 解锁更多能力</div>
          <div class="tips">选择合适你的套餐，或直接
            <a-button size="small" class="pay-power" type="link" @click="tabChange('power')">购买算力</a-button>
          </div>
        </div>
        <div class="member-list" v-if="payType==='vip'">
          <div class="member-list-item" v-for="item in _data.list" :key="item.id"
               :class="[{active:_data.checkVipInfo.id === item.id},'col-'+ _data.list.length ]"
               @click="chooseVipProduct(item,'vip')">
            <div class="list-title">{{ item.description }}</div>
            <div class="list-gift">{{ item.gift_points }}/{{ monthObj[item.method] }}</div>
            <div class="list-count">
              <i class="iconfont icon-renmingbi"></i>
              <span>{{ getPrice(item.price) }}</span>
              <span class="unit">{{ monthObj[item.method] }}</span>
            </div>
            <div class="list-btn">
              <a-button class="btn" :class="{ active:_data.checkVipInfo.id === item.id}" type="primary" size="large" block
                        @click="pay(item)">
                {{ item.price === '0.00' ? '免费使用' : '开通奇画会员' }}
              </a-button>
              <!--              <a-button class="btn" v-if="_data.checkInfo.id!== item.id"   type="primary" size="large" block @click="pay">开通奇画会员</a-button>-->
              <!--              <a-button class="btn active" v-if="_data.checkInfo.id === item.id"  type="primary" size="large" block @click="pay">开通奇画会员</a-button>-->
            </div>
            <div class="list-subheading text-center" v-if="item.points !==0"><i
                class="iconfont icon-jifen"></i>{{ item.points }}算力
            </div>
            <div class="list-subheading text-center" v-if="item.points ===0"><i class="iconfont icon-jifen"></i>每天登录赠送60算力
            </div>
            <div class="equity-list">
              <div class="equity-list-item" v-for="cItem in getAbout(item.about)">
                <CheckOutlined/>
                {{ cItem }}
              </div>
            </div>
          </div>
        </div>
        <div class="title-tab text-center" v-if="payType==='power'">
          <div class="tab-btn" @click="tabChange('vip')">购买套餐</div>
          <div class="tab-btn active">算力充值</div>
        </div>
<!--        <div class="title-points-h5 text-center" v-if="payType==='power'">-->
<!--          <div>购买算力</div>-->
<!--        </div>-->
        <div class="content-box" v-if="payType==='power'">
          <div class="product-box">
            <div class="points-list flex">
              <div class="points-list-item flex items-center justify-center" v-for="(item,index) in _data.pointLlist" :key="item.id"
                   :class="{active:_data.checkInfo.id === item.id}" @click="chooseProduct(item,'points')">
                <div>
                  <div class="list-title text-center flex justify-center items-center"><i class="iconfont icon-jifen"></i>{{ item.points }}
                  </div>
                  <div class="list-count text-center flex justify-center items-center">
                    <i class="iconfont icon-renmingbi"></i>{{ item.price }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="power-tips">
          1.  算力点有效期：您单独购买的算力点，为永久有效。<br>
          2.  充值VIP赠送算力点会与您会员到期时间同时失效，会员续期可累计。<br>
          3.  算力点消耗规则：当您运行AI 应用时，系统将以根据不同任务类型和运行次数或时间扣除相应算力点，具体以功能标注为准<br>
          4.  购买说明:基于产品的特殊性，一旦您完成付款，本产品不支持退订。<br>
        </div>
        <div class="to-pay flex justify-end items-center" v-if="payType==='power'">
          <div class="pay-price flex justify-center items-center">实付款：<i class="iconfont icon-renmingbi"></i><span>{{ _data.checkInfo.price }}</span></div>
          <a-button class="pay-btn" type="primary"   @click="pay(_data.checkInfo)">立即购买</a-button>
        </div>
      </a-spin>
    </div>
  </div>
  <payModal ref="payModalRef"></payModal>
</template>

<script setup>
import {ref, reactive, computed} from 'vue'
import {CheckOutlined} from '@ant-design/icons-vue';
import payModal from "@/components/modules/userTools/payModal.vue";
import {getProList} from "@/api/pay.js";
import router from "@/router/index.js";
import {useRoute} from "vue-router";
const route = useRoute()

const payModalRef = ref()
const _data = reactive({
  visible: false,
  loading: false,
  checkVipInfo: {},
  checkInfo: {},
  type: 'vip',
  list: [],
})
const payType = computed(() => {
  let type = route.query&&route.query.type?  route.query.type : 'vip'
  if(type!=='vip'&&type!=='power')  type = 'vip'
   return type
});
const monthObj = {
  'vip1': '月',
  'vip2': '6个月',
  'vip3': '每年'
}
const getPrice = (str) => {
   if(str) return str.replace('.00', '')
}
const initList = () => {
  _data.loading = true
  getProList({
    method: 'vip'
  }).then(res => {
    _data.list = res.data
    _data.checkVipInfo = res.data[2]
    initListPoints()
  })
}
initList()
const getAbout = (text) => {
  if (text) {
    return text.split('|')
  } else {
    return []
  }
}
const tabChange = (type) => {
  router.replace({
    path: '/recharge',
    query: {
      type: type
    }
  })
}
const initListPoints = () => {
  getProList({method: 'pp'}).then(res => {
    _data.pointLlist = res.data
    _data.checkInfo = res.data[0]
    _data.loading = false
  })
}
const chooseVipProduct = (item,type) => {
  if (_data.checkVipInfo.id === item.id) return
  _data.checkVipInfo = item
}
const chooseProduct = (item,type) => {
  if (_data.checkInfo.id === item.id) return
  _data.checkInfo = item
}
const pay = (item) => {
  if (payType.value === 'vip'&&item.price ==='0.00') {
    router.push({
      path: '/home',
    })
    return
  }
  payModalRef.value.open(item)
}

</script>

<style lang="less" scoped>
.recharge-box {
  margin: auto;
  height: 100%;
  overflow: auto;
}

.member-content {
  width: 100%;
  max-width: 1300px;
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

      .pay-power {
        line-height: 20px;
        padding: 0 5px;
      }
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
    margin-top: 50px;
    display: flex;
    align-items: stretch; /* 默认值，子元素高度会拉伸到一致 */

    .member-list-item {
      cursor: pointer;
      background: #181B21;
      //display: inline-block;
      width: calc(33% - 16px);
      padding: 25px 15px;
      margin: 8px;
      border-radius: 12px;

      .list-btn {
        padding: 15px 0;

        .btn {
          background: #199CFF;
          color: #000000;
          border-radius: 8px;
          border: 0;
          transition: none !important;

          &:hover {
            opacity: 0.8;
          }
        }
      }

      &.active {
        background: url("../../assets/image/vip_02.png") no-repeat;
        background-size: 100% 100%;
        border: 2px solid rgba(0, 138, 254, 0.5);

        .list-btn {
          .active {
            background: url("../../assets/image/active_bg_btn.png") no-repeat;
            background-size: 100% 100%;
          }
        }
      }

      &.col-4 {
        width: calc(25% - 16px);
      }

      &.col-5 {
        width: calc(20% - 16px);
      }

      .list-title {
        color: #ffffff;
        font-size: 20px;
        padding: 5px 0;
      }

      .list-gift {
        text-decoration: line-through;
      }

      .list-count {
        font-size: 16px;
        color: #199CFF;

        span {
          font-size: 36px;
          padding: 0 5px 0 0;
        }

        .unit {
          color: #919293;
          font-size: 16px;
        }
      }

      .list-subheading {
        font-size: 14px;
        color: #00B1FE;
        line-height: 20px;
        padding: 10px 0;
        margin-top: 10px;
        background: rgba(127, 127, 127, .2);
        border-radius: 8px;

        .iconfont {
          color: #00B1FE;
        }
      }

      .equity-list {
        padding: 10px 5px;

        .equity-list-item {
          color: #C8C9C9;
          line-height: 30px;
          font-size: 12px;

          :deep(.anticon.anticon-check) {
            font-size: 12px;
            margin-right: 5px;
          }
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

  .title-tab {
    padding: 15px 0 10px;
    .tab-btn{
      display: inline-block;
      margin:20px;
      padding-bottom: 5px;
      cursor: pointer;
      font-size: 24px;
      color: #87959C;
      &.active{
        color: #FFFFFF;
        position: relative;
        &:before{
          content: "";
          display:  block;
          height: 3px;
          width: 100%;
          background: #199CFF;
          position: absolute;
          bottom: 0;
          left: 0;
        }
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
        background:#181B21;
        width: calc(20% - 16px);
        padding: 15px;
        height: 200px;
        margin: 8px;
        border-radius: 5px;

        &.active {
          border: 2px rgba(78, 117, 175, 0.8) solid;

          //background: url("../../assets/image/active_bg_btn.png") no-repeat;
          //background-size: 100% 100%;
        }

        .list-title {
          height: 40px;
          font-size: 40px;
          color: #ffffff;
          .iconfont {
            color: #00B1FE;
            height: 54px;
            font-size: 36px;
          }
        }

        .list-count {
          color: #9a9898;
          font-size: 24px;

          .iconfont {
            height: 26px;
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
  .power-tips{
    padding: 10px;
    margin-top: 30px;
    font-size: 13px;
    line-height: 30px;
    color: #747474;
  }
  .to-pay{
    margin: 80px 10px 0;
    border-radius: 60px;
    padding: 15px;
    background:#181B21;
    .pay-price{
      font-size: 14px;
      .iconfont{
        color: #BBBBBC;
        height: 18px;
        line-height: 18px;
        font-size: 18px;
      }
      span{
        color: #BBBBBC;
        font-size:  26px;
        line-height: 30px;
      }
    }
    .pay-btn{
      border-radius: 20px;
      line-height: 30px;
      margin:0 10px;
      font-size: 14px;
    }
  }
}
</style>
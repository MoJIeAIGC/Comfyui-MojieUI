<template>
  <a-layout>
    <HeadMenu/>
    <a-layout style="height: calc(100vh - 51px);margin-top: 51px;overflow: hidden">
      <a-layout-sider width="160" v-model:collapsed="_data.collapsed" :trigger="null" collapsible>
        <div class="menu-btn" :class='{
          "text-right":!_data.collapsed,
          "text-center":_data.collapsed }' @click="toggleCollapsed">
          <MenuUnfoldOutlined v-if="_data.collapsed" :style="_data.iconStyle"/>
          <MenuFoldOutlined v-else :style="_data.iconStyle"/>
        </div>
        <div class="menu-box" :class="{close:_data.collapsed}">
          <a-menu v-model:selectedKeys="_data.selectedKeys" theme="dark" mode="inline">
            <template v-for="item in _data.menuList" :key="item.id">
              <a-menu-item v-if="!item.isBr" :key="item.path ?item.path:item.id" @click="toPath(item)">
                <template #icon>
                  <i :class="'iconfont ' + item.icon "></i>
                </template>
                <span>{{ item.name }}</span>
              </a-menu-item>
              <div class="br" v-if="item.isBr"></div>
            </template>
          </a-menu>
        </div>
        <div class="footer-menu" :class="{close:_data.collapsed}">
          <a-menu v-model:selectedKeys="_data.selectedKeys" theme="dark" mode="inline" :selectable="false">
            <!--            <a-popover placement="right" overlayClassName="menu-left" trigger="click" v-if="userStore&&userStore.token">-->
            <!--              <template #content>-->
            <!--                <shareTool></shareTool>-->
            <!--              </template>-->
            <!--              <template #title></template>-->
            <!--              <a-menu-item key="kefu">-->
            <!--                <template #icon>-->
            <!--                  <i class="iconfont icon-fenxiang1"></i>-->
            <!--                </template>-->
            <!--                <span>分享</span>-->
            <!--              </a-menu-item>-->
            <!--            </a-popover>-->
            <a-menu-item key="kefu" @click="toShare" v-if="userStore&&userStore.token">
              <template #icon>
                <i class="iconfont icon-fenxiang1"></i>
              </template>
              <span>分享</span>
            </a-menu-item>
            <a-popover placement="right" overlayClassName="menu-left" trigger="click">
              <template #content>
                <div>
                  <img src="../../assets/image/customerservice.png">
                </div>
                <!--                <qrcode-vue id="qrcode-ref" ref="qrcodeRef" :value="_data.url" :margin="1" :size="200" level="H" :image-settings="_data.imageSettings"></qrcode-vue>-->
              </template>
              <template #title>
                <!--                <span>使用微信扫一扫进入聊天</span>-->
              </template>
              <a-menu-item key="kefu">
                <template #icon>
                  <i class="iconfont icon-kefu"></i>
                </template>
                <span>联系客服</span>
              </a-menu-item>
            </a-popover>
            <a-menu-item key="moble" :selectable="false">
              <template #icon>
                <i class="iconfont icon-shoujiduan"></i>
              </template>
              <span>手机端</span>
            </a-menu-item>
          </a-menu>
        </div>
        
      </a-layout-sider>
      <a-layout>
        <a-layout-content>
          <router-view :key="userStore.dataTime"></router-view>
        </a-layout-content>
      </a-layout>
    </a-layout>
    <ShareModel ref="shareModelRef"></ShareModel>
  </a-layout>
</template>
<script setup>
import {reactive, onMounted, onUnmounted, watch, ref} from 'vue';
import HeadMenu from "./headMenu.vue";
import {message, Modal} from 'ant-design-vue';
import {MenuUnfoldOutlined, MenuFoldOutlined} from '@ant-design/icons-vue';
import {useRoute, useRouter} from "vue-router";
import {useUserStore} from "@/store/userStore.js";
import ShareModel from "@/components/shareModel/index.vue";

const router = new useRouter();
const route = useRoute()
const userStore = useUserStore()
const shareModelRef = ref()
const _data = reactive({
  iconStyle: {
    fontSize: '20px'
  },
  collapsed: false,
  selectedKeys: ['/chat'],
  menuList: [
    {path: '/home', id: 1, name: '首页', icon: 'icon-shouye'},
    {path: '/gallery', id: 2, name: '画廊', icon: 'icon-hualang'},
    {path: '', id: 3, name: '', icon: '', isBr: true},
    {path: '/chat', id: 4, name: '对话', icon: 'icon-duihua'},
    // {path: '/chat?type=template',id:5,name: '模板',icon:'icon-moban',query:{type:'template' }},
    {path: '/chat?type=example', id: 6, name: '范例', icon: 'icon-fanli', query: {type: 'example'}},
    {path: '', id: 7, name: 'AI图片编辑', icon: 'icon-tupian'},
    {path: '', id: 8, name: 'AI视频编辑', icon: 'icon-shipin'},
    // {path: '/video', id: 8, name: 'AI视频编辑', icon: 'icon-shipin'},
    // {path: '/about', id: 9, name: '关于我们', icon: 'icon-shipin'},
    // {path: '/acting', id: 10, name: '图片代做', icon: 'icon-shipin'},
  ]
})
watch(() => route.path, (path, oldParams) => {
  if (route.path === '/chat' && route.query.type) {
    _data.selectedKeys = [route.path + '?type=' + route.query.type]
  } else {
    _data.selectedKeys = [route.path]
  }
}, {immediate: true});

const toggleCollapsed = () => {
  _data.collapsed = !_data.collapsed
}
const toPath = (item) => {
  if (!item.path) {
    message.success('功能开发中');
    return
  }
  router.push({
    path: item.path,
    query: item.query
  })
}
const toShare = () => {
  shareModelRef.value.open()
}
const toFiling = () => {
  window.open('https://beian.miit.gov.cn/#/Integrated/index','_blank')
}

function updateWindowWidth() {
  _data.collapsed = window.innerWidth < 1300;
}

updateWindowWidth()
onMounted(() => {
  window.addEventListener('resize', updateWindowWidth);
});

onUnmounted(() => {
  window.removeEventListener('resize', updateWindowWidth);
});

const isMobileDevice = () => {
  const userAgent = navigator.userAgent || navigator.vendor || window.opera;
  // 这些表达式用来检测不同类型的设备
  const isAndroid = /android/i.test(userAgent);
  const isiOS = /iphone|ipad|ipod/i.test(userAgent);
  const isOpera = /opera|opr/i.test(userAgent);
  const isWindows = /windows phone/i.test(userAgent);
  const isBlackberry = /blackberry/i.test(userAgent);
  const isMobile = isAndroid || isiOS || isOpera || isWindows || isBlackberry;
  if(isMobile) {
    const _Modal = Modal.info({
      closable: true,
      maskClosable: true,
      centered: true,
      title: '提示',
      content: '本页面在电脑端显示效果更佳，建议切换设备访问',
      okText: '关闭',
      okType: 'danger',
      class: 'tips-modal',
      cancelText: '取消',
      width: '500px',
      onOk() {},
      onCancel() {
        _Modal.destroy();
      },
    });
  }
}
isMobileDevice()
</script>
<style scoped lang="less">

:deep(.ant-layout) {
  background-color: @bg-page-color;
}
:deep(.ant-layout-sider) {
  background-color: @bg-page-color;
  border-right: 1px solid #252525;
}

:deep(.ant-menu.ant-menu-dark) {
  background-color: @bg-page-color;
}

.menu-btn {
  cursor: pointer;
  padding: 10px;
}

.br {
  height: 1px;
  background-color: @bg-page-two-color;
  margin: 35px 20px;
}

.menu-box {
  height: calc(100vh - 320px);
  overflow: auto;
  padding: 0 10px;

  :deep(.ant-menu-item) {
    padding: 0 6px 0 14px !important;
  }

  &.close {
    height: calc(100vh - 400px);

    :deep(.ant-menu-item) {
      padding: 0 calc(50% - 18px / 2) !important;
    }
  }
}

.footer-menu {
  height: 150px;
  padding: 0 10px;

  :deep(.ant-menu-item) {
    padding: 0 6px 0 14px !important;
  }

  &.close {
    :deep(.ant-menu-item) {
      padding: 0 calc(50% - 18px / 2) !important;
    }
  }
}

.filing-information {
  padding: 10px;
  font-size: 12px;

  &.close {
    padding: 5px;
  }
  .bei-an{
    cursor:pointer;
  }
}

:deep(.ant-menu-dark.ant-menu-dark:not(.ant-menu-horizontal) .ant-menu-item-selected) {
  // background-color: #3557FF;
  background-color: rgba(53, 87, 255, 0.19); /* 添加透明度 */
  border-radius: 15px; /* 添加圆角 */
  // background-color: @bg-page-two-color;
}

:deep(.ant-menu-dark .ant-menu-item-selected .ant-menu-item-icon, .ant-menu-dark .ant-menu-item-selected .anticon) {
  color: #3557FF;
}

:deep(.ant-menu-dark .ant-menu-item-selected .ant-menu-item-icon + span, .ant-menu-dark .ant-menu-item-selected .anticon + span) {
  // color: #3557FF;
  color: white;
}

:deep(.ant-menu-dark .ant-menu-item:hover) {
  background-color: rgba(53, 53, 58, 0.5); /* 半透明蓝色背景 */
  border-radius: 19px; /* 圆角效果 */
  transition: all 0.3s ease; /* 平滑过渡动画 */
}

.footer {
  height: 50px;
  line-height: 50px;
  text-align: center;
  padding: 0;
}
</style>
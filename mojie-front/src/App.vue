<template>
	<a-config-provider :locale="locale">
    <router-view v-slot="{ Component, route }">
      <transition :name="route.meta.transition || 'fade'">
        <component :is="Component" />
      </transition>
    </router-view>
<!--    <transition name="fade" mode="out-in">-->
<!--      <router-view></router-view>-->
<!--    </transition>-->
	</a-config-provider>
<!--  <div class="custom-cursor-mask" @mousemove="maskMousemove" @mouseup="maskMouseUp"></div>-->
  <div class="custom-cursor" id="fabric-modal-cursor"></div>
  <div class="custom-cursor" id="fabric-refine-cursor"></div>
  <div class="custom-cursor" id="fabric-eliminate-cursor"></div>
</template>
<script setup>
import {onMounted, onUnmounted} from 'vue'
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import locale from 'ant-design-vue/es/locale/zh_CN';
import emitter from "@/utils/emitter.js";
dayjs.locale('zh-cn');
const mousemove = (e) => {
  emitter.emit('fabric-modal-move',e) //产品替换鼠标移动全局监听
  emitter.emit('mousemove',e)
  emitter.emit('extend-mousemove',e) //扩图全局监听
  emitter.emit('eliminate-move',e) //内补消除全局监听
  emitter.emit('refine-move',e) //局部调整全局监听
}
const mouseup = (e) => {
  emitter.emit('mouseup',e)
  emitter.emit('fabric-modal-up',e)//产品替换鼠标up全局监听
  emitter.emit('pull-refresh',e) //下拉释放全局监听
  emitter.emit('extend-mouseup',e) //扩图全局监听
  emitter.emit('eliminate-up',e) //内补消除全局监听
  emitter.emit('refine-up',e) //局部调整全局监听
}
const refresh = (e) => {
  if(e.data==='refresh')   emitter.emit('refresh-user',e)
}
onMounted(() => {
  window.addEventListener('mousemove', mousemove)
  window.addEventListener('mouseup', mouseup)
  window.addEventListener('message', refresh);
})

onUnmounted(() => {
  window.removeEventListener('mousemove', mousemove)
  window.removeEventListener('mouseup', mouseup)
  window.removeEventListener('message', refresh)
})
</script>
<style lang="less">
@import "./assets/css/common.css";
@import "./assets/css/public.less";
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.5s;
}
.fade-enter, .fade-leave-to /* .fade-leave-active in <2.1.8 */ {
  opacity: 0;
}
body{
  background: @bg-page-color!important;
}
.custom-cursor {
  display: none;
  position: fixed;
  pointer-events: none;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  cursor: none;
  background-color: rgba(42,86,145,.4);
  z-index: 9999999999999999999;
}
</style>
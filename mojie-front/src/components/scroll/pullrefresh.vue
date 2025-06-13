
<template>
  <div
      class="pull-refresh"
      @mousedown="handlerStart"
      @mousemove="handlerMove"
  >
    <div class="refresh_tip" v-if="isDown&&distance>120">释放即可刷新...</div>
    <slot></slot>
  </div>
</template>
<script  setup>
import {onMounted, onUnmounted, ref} from "vue";
import emitter from "@/utils/emitter.js";
const distance = ref(0);
const isDown = ref(false);

const emits = defineEmits(["refreshEnd"]);
onMounted(() => {
  emitter.on('pull-refresh', handlerEnd);
})

onUnmounted(() => {
  emitter.off('pull-refresh')
})
const handlerStart = e => {
  isDown.value =true
  distance.value = 0
};
const handlerMove = e => {
  if( !isDown.value) return
  const { movementY} = e
  distance.value = distance.value + movementY;
};
const handlerEnd = e => {
  isDown.value = false
  if(distance.value>120){
    distance.value = 0;
    emits("refreshEnd");
  }
};
</script>
<style scoped>
.pull-refresh{
  height: 100%;
}
.refresh_tip {
  text-align: center;
  padding: 12px 0;
  color: #3557FF;
}
</style>
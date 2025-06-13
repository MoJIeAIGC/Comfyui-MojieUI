<template>
  <div class="left">
    <div class="left-content" @click.stop>
      <div class="flex-1">
            <generationList ref="generationListRef" :video-id="_data.sessionIdx"  @change="change"/>
      </div>
      <img @click="toCommunity" class="left_poster" src="../../assets/image/left_poster.png">
    </div>
  </div>
</template>

<script setup>
import {defineEmits, reactive, ref} from 'vue'
 import generationList from "./leftTools/generationList.vue";
const emit = defineEmits(['change']);
const generationListRef = ref()
const _data = reactive({
  sessionIdx: -1, // 当前会话下标
})
const toCommunity = () => {
  window.open('https://g070zosrd54.feishu.cn/wiki/D8WkwtEH1i6HObk0MM1cw2p0nkc?fromScene=spaceOverview', '_blank');
}
const change = (id) => {
  _data.sessionIdx = id
  emit('change', id)
}
const changeVideo = (id) => {
  if (id) {
    _data.sessionIdx = id
    generationListRef.value.refreshList(id)
  }
  // if (props.tab === 'chat') {
  //   if (chatRef.value) chatRef.value.refreshList(item)
  // }
}
defineExpose({
  changeVideo
})
</script>

<style lang="less" scoped>
.left {
  .left-content {
    display: flex;
    flex-direction: column;
    width: 300px;
    height: 100%;
    transition: 0.3s all;
    background-color: @bg-page-color;

    > .flex-1 {
      height: 0;
    }

    .left_poster {
      cursor: pointer;
      width: 100%;
      padding: 10px;
    }
  }
}

@media screen and (max-width: 1300px) {
  .left {
    .left-content {
      width: 200px;
    }
  }
}
</style>
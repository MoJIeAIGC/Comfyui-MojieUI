<template>
  <div class="left">
    <div class="left-content" @click.stop>
      <div class="flex-1">
        <newChat ref="chatRef" :chatId="_data.sessionIdx" v-if="props.tab==='chat'" @change="chatIdChange"/>
        <exampleChat ref="chatRef" v-if="props.tab==='example'" @change="chatIdChange"/>
        <!--        <templateChat ref="chatRef" v-if="props.tab==='template'" @change="chatIdChange"/>-->
      </div>
      <img @click="toCommunity" class="left_poster" src="../../assets/image/left_poster.png">
    </div>
  </div>
</template>

<script setup>
import {defineEmits, reactive, ref} from 'vue'
import newChat from "./leftTools/newChat.vue";
import exampleChat from "./leftTools/exampleChat.vue";
// import templateChat from "./leftTools/template.vue";

const chatRef = ref()
const props = defineProps({
  tab: {
    type: String,
    default: 'chat'
  }
})
const emit = defineEmits(['change']);
const _data = reactive({
  sessionIdx: -1, // 当前会话下标
})
const toCommunity = () => {
  window.open('https://g070zosrd54.feishu.cn/wiki/D8WkwtEH1i6HObk0MM1cw2p0nkc?fromScene=spaceOverview', '_blank');
}
const chatIdChange = (id) => {
  _data.sessionIdx = id
  emit('change', id)
}
const changeChat = (item) => {
  if (item && item.id) _data.sessionIdx = item.id
  if (props.tab === 'chat') {
    if (chatRef.value) chatRef.value.refreshList(item)
  }
}
defineExpose({
  changeChat
})
</script>

<style lang="less" scoped>
.left {
  .left-content {
    display: flex;
    flex-direction: column;
    width: 360px;
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
      width: 240px;
    }
  }
}
</style>
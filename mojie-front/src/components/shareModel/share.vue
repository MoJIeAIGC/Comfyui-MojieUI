<template>
    <div class="member-content">
      <img src="../../assets/image/share1.png">
        <div class="footer flex">
          <div class="flex-1">
            <div class="title">邀请好友加入奇画AI</div>
            <div class="title-tips">复制链接发送给好友，和TA一起探索视觉未来</div>
          </div>
          <div class="flex items-center">
            <a-button class="copy-btn" type="primary" size="small" @click="copyUrl">复制链接</a-button>
          </div>
        </div>
    </div>
</template>

<script setup>
import { reactive} from 'vue'
import {message} from "ant-design-vue";
import {queryUserShareCode} from "@/api/login.js";
const _data = reactive({
  share_code: '',
  url:''
})
const initList = () => {
  queryUserShareCode().then(res => {
    _data.url = window.location.origin + '/home?shareCode='+ res.data.share_code
    _data.share_code = res.data.share_code
  })
}
const copyUrl = () => {
  try {
    const textarea = document.createElement("textarea");
    textarea.value =  '奇画AI邀请您体验AI生图,点击链接体验：' + _data.url + '，邀请码:' + _data.share_code;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
    message.success('复制链接成功')
  } catch (error) {
    console.error(error);
    message.error('复制链接失败')
  }
}
initList()

</script>

<style lang="less" scoped>
.member-content {
  border-radius: 16px;
  width: 360px;
  padding:0;
  img{
    border-radius: 8px 8px 0 0;
    width: 100%;
  }
  .footer{
    padding: 15px 10px;
    border-radius:0 0 8px 8px;
    color: #FFFFFF;
    background:@bg-page-color;
    .title{
      font-size: 14px;
    }
    .title-tips{
      font-size: 12px;
    }
    .copy-btn{
      height: 30px;
      line-height: 30px;
      font-size: 12px;
      border-radius: 15px;
      border: 0;
    }
  }
}
</style>
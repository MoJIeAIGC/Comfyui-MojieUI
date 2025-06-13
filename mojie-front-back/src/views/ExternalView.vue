<script setup lang="ts">
import { ref } from 'vue';
import axios from 'axios';
import { useRoute } from 'vue-router';

const route = useRoute();
const query = route.query;
// 解码
const url = decodeURIComponent(<string>query.url);
// 用于存储 sessionid
const sessionId = ref('');
const sessionId1 = ref('');

// 发送请求获取 sessionid 的函数
const fetchSessionId = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:8000/api/image/getCaptcha', {
      withCredentials: true // 允许携带 cookie
    });

    // 从 document.cookie 中提取 sessionid
    // 从 document.cookie 中提取 sessionid
    const cookies = document.cookie.split('; ');
    for (const cookie of cookies) {
      const [name, value] = cookie.split('=');
      if (name === 'sessionid') {
        sessionId1.value = value;
        break;
      }
    }
    if (sessionId1.value) {
      console.log('方法1获取到的 Session ID:', sessionId1.value); 
    }


    const date = response.headers['date'];
    console.log('获取到的 date:', date);
    const sessionId = response.headers['set-cookie'];
    console.log('获取到的 sessionid:', sessionId);
    if (sessionId) {
        console.log('获取到');
        const match = sessionId[0].match(/session_id=([^;]+)/);
        if (match) {
            const actualSessionId = match[1];
            console.log('获取到的 Session ID:', actualSessionId);
        }
    }
  } catch (error) {
    console.error('获取 sessionid 失败:', error);
  }
};
</script>

<template>
  <div class="frame-view">
    <!-- 添加按钮 -->
    <button @click="fetchSessionId">获取 Session ID</button>
    <!-- 显示 sessionid -->
    <div v-if="sessionId">{{ sessionId }}</div>
    <!-- <keep-alive :key="url">
      <iframe :src="url" border="0" frameborder="0"></iframe>
    </keep-alive> -->
  </div>
</template>

<style scoped>
.frame-view {
  flex: 1;
  overflow: hidden;
  iframe {
    width: 100%;
    height: 100%;
  }
}
</style>
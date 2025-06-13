<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useStorage } from '@vueuse/core';
import { ElMessage, ElCard, ElRow, ElCol } from 'element-plus';
import * as echarts from 'echarts';
import { getmoney,uc } from '@/api/orderapi'; // 假设这是调用 API 的函数
import { useUserStore } from '@/store/userStore'; // 导入 userStore
const userStore = useUserStore(); // 获取 userStore 实例
// 模拟总营业额和今日营业额，实际应从 API 获取
const totalRevenue = ref(0);
const todayRevenue = ref(0);
const sevenDaysData = ref([]);
const currentTime = ref('');
let timer: ReturnType<typeof setInterval>;



const ucData = ref({
  vips: 0,
  users: 0,
  today_users: 0
});

// 新增获取uc数据的函数
const fetchUcData = async () => {
  try {
    const response = await uc();
    ucData.value = response.data;
  } catch (error) {
    ElMessage.error('获取用户数据失败');
  }
};

// 更新当前时间的函数
const updateTime = () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  currentTime.value = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
};
// 定义获取数据的函数
const fetchData = async () => {
  try {
    const response = await getmoney();
    sevenDaysData.value = response.data;
    // 计算总营业额和今日营业额，这里简单模拟，实际需根据业务逻辑处理
    totalRevenue.value = sevenDaysData.value.reduce((sum, item) => sum + item.revenue, 0);
    const today = new Date().toISOString().split('T')[0];
    const todayItem = sevenDaysData.value.find(item => item.date === today);
    todayRevenue.value = todayItem ? todayItem.revenue : 0;

    // 初始化折线图
    initChart();
  } catch (error) {
    ElMessage.error('获取数据失败');
  }
};

// 初始化折线图
const initChart = () => {
  const chartDom = document.getElementById('revenueChart');
  if (chartDom) {
    const myChart = echarts.init(chartDom);
    const dates = sevenDaysData.value.map(item => item.date);
    const revenues = sevenDaysData.value.map(item => item.revenue);
    const option = {
      xAxis: {
        type: 'category',
        data: dates
      },
      yAxis: {
        type: 'value'
      },
      series: [
        {
          data: revenues,
          type: 'line'
        }
      ]
    };
    myChart.setOption(option);
  }
};

onMounted(() => {
  fetchData();
  updateTime();
  timer = setInterval(updateTime, 1000);
  fetchUcData(); // 新增调用
});


onUnmounted(() => {
  // 组件卸载时清除定时器
  clearInterval(timer);
});
</script>

<template>
  <div style="height: 2000px">
    <!-- <div>
      <el-link type="primary" @click="showDialog"> click me</el-link>
      <el-button>Default</el-button>
    </div> -->
    <el-row :gutter="20">
      <el-col :span="3">
        <el-card style="height: 200px;">
          
          <img src="../assets/xzk.jpg"  alt="" width="100" height="100"  style="display: block; margin: 0 auto;">
          <div style="font-size: 57px; font-weight: bold; text-align: center;" >

            {{ userStore.username }}
          </div>
        </el-card> 
      </el-col>
      <el-col :span="4">
        <el-card style="height: 200px;">
          <template #header>
            <div  style="font-size: 30px; font-weight: bold; text-align: center;"  class="card-header">
              <span>总营业额</span>
            </div>
          </template>
          <div style="font-size: 60px; font-weight: bold; text-align: center;" >{{ ucData.total_revenue }}</div>
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card style="height: 200px;">
          <template #header>
            <div  style="font-size: 30px; font-weight: bold; text-align: center;"  class="card-header">
              <span>今日营业额</span>
            </div>
          </template>
          <div  style="font-size: 60px; font-weight: bold; text-align: center;"  >{{ todayRevenue }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card  style="height: 200px;">
          <!-- <template #header>
            <div  style="font-size: 30px; font-weight: bold; text-align: center;"  class="card-header">
              <span>{{ currentTime }}</span>
            </div>
          </template> -->
          <div style="font-size: 60px; font-weight: bold; text-align: center;" >{{ currentTime }}</div>


          <!-- <h1>{{ currentTime }}</h1> -->
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card style="height: 200px;">
          <!-- <template #header>
            <div  style="font-size: 30px; font-weight: bold; text-align: center;"  class="card-header">
              <span>用户总数</span>
            </div>
          </template>
          <div  style="font-size: 60px; font-weight: bold; text-align: center;"  >{{ ucData.users }}</div> -->
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6">
        <el-card style="height: 200px;">
          <template #header>
            <div  style="font-size: 30px; font-weight: bold; text-align: center;"  class="card-header">
              <span>用户总数</span>
            </div>
          </template>
          <div  style="font-size: 60px; font-weight: bold; text-align: center;"  >{{ ucData.users }}</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card style="height: 200px;">
          <template #header>
            <div  style="font-size: 30px; font-weight: bold; text-align: center;"  class="card-header">
              <span>今日新增用户</span>
            </div>
          </template>
          <div style="font-size: 60px; font-weight: bold; text-align: center;" >{{ ucData.today_users }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card style="height: 200px;">
          <template #header>
            <div  style="font-size: 30px; font-weight: bold; text-align: center;"  class="card-header">
              <span>会员总数</span>
            </div>
          </template>
          <div  style="font-size: 60px; font-weight: bold; text-align: center;"  >{{ ucData.vips }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card  style="height: 200px;">
          <!-- <template #header>
            <div  style="font-size: 30px; font-weight: bold; text-align: center;"  class="card-header">
              <span>{{ currentTime }}</span>
            </div>
          </template> -->
          <!-- <div style="font-size: 60px; font-weight: bold; text-align: center;" >{{ currentTime }}</div> -->


          <!-- <h1>{{ currentTime }}</h1> -->
        </el-card>
      </el-col>
      
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="23">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>七天营业额折线图</span>
            </div>
          </template>
          <div id="revenueChart" style="height: 400px;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

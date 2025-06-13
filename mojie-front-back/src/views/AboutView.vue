<script setup lang="ts">
import { useStorage,useDark } from '@vueuse/core';
const welcome = useStorage('welcome', 'Welcome to Simple UI!');


const isDark=useDark()

</script>
<template>
  <el-checkbox v-model="isDark">Dark Mode</el-checkbox>
  <div class="about">
    {{ welcome }}
    <h1>This is an about page</h1>
    <button>Click me</button>
    <el-button>Default</el-button>
    {{ isDark }}
    <!-- 切换主题 -->
    <el-button type="primary" @click="isDark=!isDark">Toggle{{ isDark }}</el-button>

    <el-card style="max-width: 480px"   >
      <template #header>
        <div class="card-header">
          <span>Card name</span>
        </div>
      </template>
      <p v-for="o in 4" :key="o" class="text item">{{ 'List item ' + o }}</p>
      <template #footer>Footer content</template>
    </el-card>
  </div>
</template>

<style>
@media (min-width: 1024px) {
  .about {
    min-height: 100vh;
    display: flex;
    align-items: center;
  }
}
</style>

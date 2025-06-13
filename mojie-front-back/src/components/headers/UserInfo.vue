<script setup lang="ts">
import {Close, HomeFilled, User} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from 'element-plus';
import { useRouter } from 'vue-router';
import { logout as apiLogout } from '@/api/userApi'; // 导入登出 API 函数
import { useTokenStore } from '@/store/tokenStore'; // 导入 userStore
import { useUserStore } from '@/store/userStore'; // 导入 userStore
const userStore = useUserStore();

const tokenStore = useTokenStore();
const router = useRouter();


function logout() {
  ElMessageBox.confirm("确认退出登录吗？", "提示", {
    confirmButtonText: "确认",
    cancelButtonText: "取消",
    type: "warning",
  }).then(async () => {
    try {
      // 调用登出 API
      await apiLogout();
      // 清除用户信息
      tokenStore.clearTokens();
      ElMessage({
        type: "success",
        message: "退出成功",
      });
      // 跳转到登录页
      router.push("/login"); 
    } catch (error) {
      ElMessage({
        type: "error",
        message: "登出失败，请稍后重试",
      });
      console.error("登出失败", error);
    }
  }).catch(() => {
    // 用户取消登出操作
    ElMessage({
      type: "info",
      message: "登出操作已取消",
    });
  });
}

const userInfo = {
  name: userStore.username,
  avatar: new URL('@/assets/xzk.jpg', import.meta.url).href 
}
// const router = useRouter()

function to(url: any) {
  router.push(url)
}
</script>

<template>
  <el-dropdown trigger="click">
    <div class="user">
      <el-avatar :src="userInfo.avatar"/>
      <span>{{ userInfo.name }}</span>
    </div>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item @click="to('/')">
          <el-icon>
            <HomeFilled/>
          </el-icon>
          {{ $t('Home') }}
        </el-dropdown-item>
        <el-dropdown-item divided @click="to('/profile')">
          <el-icon>
            <User/>
          </el-icon>
          {{ $t('Profile') }}
        </el-dropdown-item>

        <el-dropdown-item divided @click="logout">
          <el-icon>
            <Close/>
          </el-icon>
          {{ $t('Logout') }}
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>

</template>

<style scoped>
.user {
  cursor: pointer;
  display: flex;
  gap: 10px;
  align-items: center;

}
</style>
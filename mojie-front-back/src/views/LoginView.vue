<script setup lang="ts">
import SwitchLanguage from "@/components/headers/SwitchLanguage.vue";
import SwitchDarkMode from "@/components/headers/SwitchDarkMode.vue";
import { useStorage } from "@vueuse/core";
import { ref, reactive, computed } from "vue";
import { useRouter } from "vue-router";
import { t } from "@/messages/i18n";
import { Loading } from "@element-plus/icons-vue";
import { login } from "@/api/userApi"; // 导入 login 函数
import { useTokenStore } from '@/store/tokenStore'; // 导入 userStore
import { useUserStore } from '@/store/userStore'; // 导入 userStore
import { ElMessage } from 'element-plus';
const username = ref("");
const password = ref("");

const rememberMe = useStorage("rememberMe", false);
const router = useRouter();

const formRef = ref(null);

const form = reactive({
  username: "",
  password: "",
});
const rules = computed(() => {
  return {
    username: [
      {
        required: true,
        message: t("Username is required"),
        trigger: "change",
      },
    ],
    password: [
      {
        required: true,
        message: t("Password is required"),
        trigger: "change",
      },
    ],
  };
});
const isLoading = ref(false);

const tokenStore = useTokenStore();
const userStore = useUserStore();

const submit = async () => {
  formRef.value?.validate(async (valid) => {
    console.log("valid", valid);
    if (valid) {
      isLoading.value = true;
      try {
        const formData = new FormData();
        formData.append("user_name", form.username);
        formData.append("password", form.password);

        const response = await login(formData);
        console.log("登录响应", response.code);
        if (response && response.code === 200) {
          // 请求成功，跳转到首页
          const { access_token, refresh_token ,userId,username} = response.data
          ElMessage.success(t('Login successful'));
          tokenStore.setTokens(access_token, refresh_token)
          userStore.setUserId(userId)
          userStore.setUsername(username)
          router.push("/");
        } else {
          ElMessage.error(t('Login failed'));
          console.error("登录失败", response);
        }
      } catch (error) {
        console.error("用户登录失败", error);
      } finally {
        isLoading.value = false;
      }
    }
  });
};
</script>

<template>
  <div class="login">
    <div class="main">
      <div class="logo" >
        <img src="../assets/logo.svg"  alt=""  width="200" height="100" />
      </div>
      <div class="title">{{ $t("Sign in to your account") }}</div>
      <el-card class="card">
        <el-form
          ref="formRef"
          label-position="top"
          :rules="rules"
          status-icon
          :model="form"
        >
          <el-form-item :label="$t('Username')" prop="username">
            <el-input v-model="form.username" clearable></el-input>
          </el-form-item>
          <el-form-item :label="$t('Password')" prop="password">
            <el-input
              v-model="form.password"
              clearable
              type="password"
              show-password
            ></el-input>
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="rememberMe">{{ $t("Remember me") }}</el-checkbox>
          </el-form-item>
          <div class="flex btn">
            <el-button type="primary" @click="submit" :disabled="isLoading">
              <el-icon class="is-loading" v-if="isLoading">
                <Loading />
              </el-icon>
              <span v-else>{{ $t("Sign in") }}</span>
            </el-button>
          </div>
        </el-form>
        <el-divider />
        <div class="flex justify-between action">
          <div class="flex">
            {{ $t("Language") }}:
            <SwitchLanguage />
          </div>
          <SwitchDarkMode />
        </div>
      </el-card>
      <div class="tips">
        {{ $t("Not a member? Please contact the administrator") }}
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
body {
  background-color: var(---login-bg);
}

.login {
  background-color: var(---login-bg);
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;

  .main {
    display: flex;
    gap: 20px;
    flex-direction: column;
    justify-content: center;
    align-items: center;

    .title {
      color: var(--el-text-color-primary);
      line-height: 2.25rem;
      font-weight: 700;
      font-size: 1.5rem;
    }
  }

  .card {
    padding: 50px;

    min-width: 400px;

    .btn {
      .el-button {
        flex: 1;
      }
    }
  }

  .logo {
    min-width: 50px;
    min-height: 50px;
  }

  .tips {
    color: var(--el-text-color-secondary);
  }

  .action {
    width: 100%;
  }
}
</style>@/store/userStore
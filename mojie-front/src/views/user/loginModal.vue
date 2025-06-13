<template>
  <div class="login-wp">
    <div class="content">
      <div class="content-box">
        <close-circle-filled class="close-login-modal" @click="closeLogin" :style="iconStyle"/>
        <template v-if="_data.isRegister==='isRegister'">
          <URegister @back="tuUserLogin"/>
        </template>
        <template v-else-if="_data.isRegister==='forgotPassword'">
          <forgotPassword @back="tuUserLogin"/>
        </template>
        <template v-else>
          <div class="title-h5">登录即可使用 奇画</div>
          <div class="title-tips">奇画3.0&万物迁移-中文输出产品海报.</div>
          <a-form class="t-form" ref="formRef" :model="_data.form" :rules="_data.rules">
            <template v-if="_data.loginType==='user'">
              <a-form-item name="name">
                <a-input class="ipt" v-model:value="_data.form.name" placeholder="请输入邮箱/手机号"
                         @keyup.enter="doLogin">
                  <template #prefix>
                    <i class="iconfont icon-geren" :style="iconStyle"></i>
                    <!--                    <UserOutlined :style="iconStyle"/>-->
                  </template>
                </a-input>
              </a-form-item>
              <a-form-item name="password">
                <a-input-password class="ipt" v-model:value="_data.form.password" placeholder="请输入密码"
                                  autocomplete="off" @keyup.enter="doLogin">
                  <template #prefix>
                    <i class="iconfont icon-mima" :style="iconStyle"></i>
                    <!--                    <LockOutlined :style="iconStyle"/>-->
                  </template>
                </a-input-password>
              </a-form-item>
              <a-form-item name="code" v-if="errorLogin===1">
                <a-input class="ipt code-btn" v-model:value="_data.form.code" :maxlength="4"
                         placeholder="请输入验证码，不区分大小写"
                         autocomplete="off" @keyup.enter="doLogin">
                  <template #prefix>
                    <LockOutlined :style="iconStyle"/>
                  </template>
                  <template #suffix>
                    <img class="code-image" @click="refreshCode" style="height: 40px" :src="'data:image/jpeg;base64,'+codeUrl" alt="">
                  </template>
                </a-input>
              </a-form-item>
            </template>
            <template v-if="_data.loginType==='email'">
              <a-form-item name="mail">
                <a-input class="ipt" v-model:value="_data.form.mail" placeholder="请输入邮箱/手机号"
                         @keyup.enter="doLogin">
                  <template #prefix>
                    <i class="iconfont icon-geren" :style="iconStyle"></i>
                  </template>
                </a-input>
              </a-form-item>
              <a-form-item name="code">
                <a-input class="ipt code-btn" v-model:value="_data.form.code" :maxlength="5" placeholder="请输入验证码"
                         autocomplete="off" @keyup.enter="doLogin">
                  <template #prefix>
                    <LockOutlined :style="iconStyle"/>
                  </template>
                  <template #suffix>
                    <a-button type="link" :disabled="_data.down.n > 0||_data.disSendCode" @click="downTime('email')">
                      {{ _data.down.n > 0 ? _data.down.n + "s" : '发送验证码' }}
                    </a-button>
                  </template>
                </a-input>
              </a-form-item>
            </template>
            <a-form-item class="text-center">
              <div class="flex" style="gap: 20px;">
                <a-button class="btn" type="primary"
                          :disabled="_data.btnLoading"
                          @click="doLogin()">
                  登录
                </a-button>
              </div>
            </a-form-item>
            <div class="flex">
              <div class="flex-1 text-left" v-if="_data.loginType!=='user'">
                <a-button type="link" @click="changeLoginType('user')">密码登录</a-button>
              </div>
              <div class="flex-1 text-left" v-if="_data.loginType!=='email'">
                <a-button type="link" @click="changeLoginType('email')">验证码登录</a-button>
              </div>
              <div class="flex-1 text-center" v-if="_data.loginType==='user'">
                <a-button type="link" @click="_data.isRegister='forgotPassword'">忘记密码？</a-button>
              </div>
              <div class="flex-1 text-right">
                <a-button type="link" @click="_data.isRegister='isRegister'">去注册</a-button>
              </div>
            </div>
          </a-form>
        </template>
      </div>
    </div>
    <!--    <loginBg/>-->
  </div>
</template>

<script setup>
import {createVNode, reactive, ref} from 'vue'
import {Modal, notification} from "ant-design-vue";
import {LockOutlined, ExclamationCircleOutlined, CloseCircleFilled} from "@ant-design/icons-vue";

import {loginByPhone, getCode, loginByEmail, getEmailCode, loginByUser,getCaptcha} from "@/api/login.js";
import md5 from 'md5';
import {useUserStore} from "@/store/userStore.js";
import URegister from './register.vue'
import forgotPassword from './forgotPassword.vue'
import {useOrderStore} from "@/store/orderStore.js";
const userStore = useUserStore();
const orderStore = useOrderStore();
const formRef = ref();
const iconStyle = {
  fontSize: '24px',
  color: '#fff'
}
const reg = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
const regPhone = /^1[3-9]\d{9}$/

const codeUrl =  ref()
const errorLogin =  ref(0)
const _data = reactive({
  isRegister: false,
  btnLoading: false,
  disSendCode: false,
  loginType: 'user', // phone user
  typeIndex: 1,

  // 倒计时
  down: {
    t: null,
    n: 0
  },

  form: {
    cellphone: '',
    name: '',
    mail: '',
    password: '',
    code: '',
    agree: false
  },
  rules: {
    name: [
      {
        required: true, validator: async (_rule, value) => {
          if (value === '') {
            return Promise.reject('请输入邮箱或手机号');
          }
          if (!reg.test(value) && !regPhone.test(value)) return Promise.reject('请输入正确的邮箱或手机号');
          return Promise.resolve();
        }
      }
    ],
    password: [{required: true, message: '请输入密码'}],
    mail: [{
      required: true, validator: async (_rule, value) => {
        if (value === '') {
          return Promise.reject('请输入邮箱或手机号');
        }
        if (!reg.test(value) && !regPhone.test(value)) return Promise.reject('请输入正确的邮箱或手机号');
        return Promise.resolve();
      }
    }],
    cellphone: [
      {
        required: true, validator: async (_rule, value) => {
          if (value === '') {
            return Promise.reject('请输入手机号');
          }
          if (!/^1[3-9]\d{9}$/.test(value)) return Promise.reject('手机号格式不正确');
          return Promise.resolve();
        }
      }
    ],
    code: [{required: true, message: '请输入验证码'}],
    agree: [{
      required: true, validator: async (_rule, value) => {
        if (!value) {
          return Promise.reject('请阅读并同意用户协议和隐私条款');
        }
        return Promise.resolve();
      }
    }],
  }
})

function doLogin() {
  formRef.value.validate().then(() => {
    if (_data.loginType === 'email') {
      _data.btnLoading = true;
      _data.disSendCode = true
      if (reg.test(_data.form.mail)) {
        loginByEmail({mail: _data.form.mail, code: _data.form.code}).then(res => {
          notification.success({
            message: '提示',
            description: '登录成功'
          });
          userStore.setUserinfo(res.data);
          userStore.setToken(res.data.access_token);
          userStore.setShowLogin(false)
          orderStore.setOrderInfo({})
          // location.reload();
        }, (err) => {
          if (err.data.message === '用户不存在') {
            Modal.confirm({
              title: '提示',
              centered: true,
              icon: createVNode(ExclamationCircleOutlined),
              content: '您的邮箱还没有注册，是否去注册？',
              onOk() {
                _data.isRegister = true
              },
              // eslint-disable-next-line @typescript-eslint/no-empty-function
              onCancel() {
              },
            });
          }
        }).finally(() => {
          _data.btnLoading = false;
        })
      }
      if (regPhone.test(_data.form.mail)) {
        loginByPhone({phone: _data.form.mail, code: _data.form.code}).then(res => {
          notification.success({
            message: '提示',
            description: '登录成功'
          });
          userStore.setUserinfo(res.data);
          userStore.setToken(res.data.access_token);
          userStore.setShowLogin(false)
          orderStore.setOrderInfo({})
        }).finally(() => {
          _data.btnLoading = false;
        })
      }
    }
    if (_data.loginType === 'user') {
      _data.btnLoading = true;
      loginByUser({
        usermail: _data.form.name,
        password: md5(md5(_data.form.password)),
        code: _data.form.code
      }).then(res => {
        notification.success({
          message: '提示',
          description: '登录成功'
        });
        userStore.setUserinfo(res.data);
        userStore.setToken(res.data.access_token);
        userStore.setShowLogin(false)
        orderStore.setOrderInfo({})
        //location.reload();
      }).finally(() => {
        refreshCode()
        _data.btnLoading = false;
      })
    }
  })
}

// 倒计时
function downTime() {
  if (_data.down.n > 0 || _data.disSendCode) {
    return;
  }
  if (_data.loginType === 'email') {
    formRef.value.validate(['email']).then(() => {
      _data.disSendCode = true
      if (reg.test(_data.form.mail)) {
        getEmailCode({mail: _data.form.mail}).then(res => {
          notification.success({
            message: '提示',
            description: '发送成功'
          });
          _data.down.n = 60;
          _data.disSendCode = false
          _data.down.t = setInterval(() => {
            _data.down.n--;
            if (_data.down.n <= 0) {
              clearInterval(_data.down.t);
            }
          }, 1000);
        }, err => {
          _data.disSendCode = false
          _data.down.n = 0;
        })
      }
      if (regPhone.test(_data.form.mail)) {
        getCode({phone: _data.form.mail}).then(res => {
          notification.success({
            message: '提示',
            description: '发送成功'
          });
          _data.down.n = 60;
          _data.disSendCode = false
          _data.down.t = setInterval(() => {
            _data.down.n--;
            if (_data.down.n <= 0) {
              clearInterval(_data.down.t);
            }
          }, 1000);
        }, err => {
          _data.disSendCode = false
        })
      }
    })
  }
}

const changeLoginType = (type) => {
  _data.loginType = type
  _data.form = {cellphone: '', name: '', mail: '', password: '', code: ''}
}
const tuUserLogin = (type) => {
  refreshCode()
  _data.isRegister = false
}
const closeLogin = () => {
  userStore.setShowLogin(false)
}
const refreshCode = () => {
  getCaptcha().then((res) => {
    codeUrl.value= res.data.image_data
    errorLogin.value= res.data.errorlogin
  })
}
refreshCode()
</script>

<style lang="less" scoped>
.login-wp {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999999;
  // background: linear-gradient(to bottom right, #0B0C13, #0D1D40, #2F1A34);
  background: rgba(133, 128, 128, 0.3);

  .content {
    position: absolute;
    padding: 30px 0;
    top: 50%;
    left: 50%;
    width: 460px;
    max-width: 78vw;
    background: rgba(0, 0, 0, .9);
    transform: translate(-50%, -50%);
    box-shadow: 0 0 12px 0 rgb(0 0 0 / 10%);
    border-radius: 16px;
    display: flex;
    z-index: 99;

    .content-box {
      position: relative;
      width: 460px;
      height: 490px;
      padding: 0 30px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: #ffffff;

      .close-login-modal {
        cursor: pointer;
        position: absolute;
        top: -30px;
        right: 5px;
      }

      .title-h5 {
        font-size: 28px;
        padding: 0 0 20px;
      }

      .title-tips {
        font-size: 18px;
        color: #999999;
        padding: 10px 0 20px;
      }

      .t-form {
        width: 100%;

        //:deep(.ant-form-item) {
        //  padding-top: 20px;
        //}

        .ipt {
          border-radius: 8px;
          height: 50px;
          background-color: inherit;
          border-color: #242837;

          :deep(.ant-input) {
            color: #fff;
            font-size: 16px;
            background-color: inherit;
          }

          :deep(.ant-input-prefix) {
            margin-right: 10px;
          }

          :deep(.ant-input-password-icon,.anticon-eye,.ant-btn-link) {
            color: #fff;
          }

          :deep(.ant-btn-link) {
            color: #7B74DB;
          }

          :deep(.ant-btn-link[disabled],.ant-btn-link[disabled]:hover) {
            color: #999
          }

          .code-image {
            height: 40px;
            min-width: 60px;
            cursor: pointer;
            border-radius: 3px;
          }
        }

        .btn {
          flex: 1;
          height: 50px;
          font-size: 16px;
          border-radius: 8px;
          border: 0;
          background: @btn-bg-color;
        }

        .agree .agree-item {
          color: #999;
          font-size: 16px;
          line-height: 40px;

          :deep(.ant-btn-link) {
            padding: 0;
            font-size: 16px;
            height: 40px;
            color: #7B74DB;
          }

          .agree-check {
            margin-right: 6px;

            :deep(.ant-checkbox-inner) {
              // 设置 checkbox 的大小
              width: 24px;
              height: 24px;
              font-size: 20px;
              background-color: inherit;
              border-color: #7B74DB;
              // 设置对勾的 大小 和 位置
              &::after {
                top: 8px;
                left: 3px;
                width: 9px;
                height: 17px;
                border-color: #7B74DB;
              }
            }

            :deep(.ant-checkbox) {
              top: 6px;

              &::after {
                display: none;
                border: 0;
              }
            }

          }
        }
      }

      .text-right, .text-left {
        :deep(.ant-btn-link) {
          color: #9C9C9E;
        }
      }
    }
  }
}

@media screen and (max-width: 600px) {
  .login-wp {
    .content {
      display: block;
      width: 90vw;
      max-width: none;
      margin-top: -35vh;
      margin-left: -45vw;
      background: rgba(0, 0, 0, .9);
      z-index: 99;
      transform: translate(0, 0);

      .content-box {
        &:before {
          display: none;
        }

        width: 100%;
        height: auto;
        padding: 15px;
      }
    }
  }
}
</style>
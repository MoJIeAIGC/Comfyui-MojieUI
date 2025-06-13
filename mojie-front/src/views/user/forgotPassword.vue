<template>
  <div class="register-wp">
    <div class="form-box">
      <div class="title">忘记密码</div>
      <a-form class="t-form" labelAlign="left" ref="registerFormRef" :rules="_data.rules" :model="_data.form" :label-col="{style: {width: '100px'}}">
        <a-form-item name="systemUserId">
          <a-input class="ipt" v-model:value="_data.form.systemUserId" placeholder="请输入邮箱/手机号">
            <template #prefix>
              <i class="iconfont icon-geren" :style="iconStyle"></i>
            </template>
          </a-input>
        </a-form-item>
        <a-form-item name="code">
          <a-input class="ipt" v-model:value="_data.form.code" :maxlength="5" placeholder="请输入验证码">
            <template #prefix>
              <LockOutlined :style="iconStyle"/>
            </template>
            <template #suffix>
              <a-button type="link" :disabled="_data.time.n > 0|| _data.disSendCode" @click="sendCode()">
                {{ _data.time.n > 0 ? _data.time.n + "s" : '获取验证码' }}
              </a-button>
            </template>
          </a-input>
        </a-form-item>
        <a-form-item name="password">
          <a-input-password  class="ipt" v-model:value="_data.form.password" autocomplete="off" placeholder="请输入新密码">
            <template #prefix>
              <i class="iconfont icon-mima" :style="iconStyle"></i>
            </template>
          </a-input-password>
        </a-form-item>
        <a-form-item name="password2">
          <a-input-password  class="ipt" v-model:value="_data.form.password2" autocomplete="off" placeholder="请再次输入新密码">
            <template #prefix>
              <i class="iconfont icon-mima" :style="iconStyle"></i>
            </template>
          </a-input-password>
        </a-form-item>
      </a-form>
      <div class="text-center flex">
        <a-button class="sub-btn btn" type="primary" @click="submit">确定</a-button>
      </div>
      <div class="text-right">
        <a-button class="sub-btn" type="link"  @click="backLogin">返回登录</a-button>
      </div>
    </div>
  </div>
</template>

<script setup>
	import { reactive, ref, defineEmits } from 'vue'
	import {notification} from "ant-design-vue";

	import {Verify} from "@/utils/Tools.js";
  import {getCode, getEmailCode, forgotPasswordRepass} from "@/api/login.js";
  import md5 from 'md5';
  import {LockOutlined} from "@ant-design/icons-vue";
  import {useUserStore} from "@/store/userStore.js";
  const userStore = useUserStore();
  const registerFormRef = ref()
  const reg = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
  const regPhone = /^1[3-9]\d{9}$/
  const iconStyle = {
    fontSize: '24px',
    color: '#fff'
  }
  let _password = ''
  let _password2 = ''
	const _data = reactive({
    disSendCode: false,
		form: {
			code: '',
			name: '',
			password: '',
			password2: '',
			systemUserId: ''
		},
		time: {
			n: 0,
			t: null
		},

		rules: {
      systemUserId: [
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
      password: [
        { required: true, validator: (_rule, value) => {
            if (!value) {
              return Promise.reject('请输入密码');
            }
            if(!Verify.password.test(value)) return Promise.reject('密码为6-20位的数字字母组成');
            if(_data.form.password2&&value !== _data.form.password2) {
              _password = 'err'
              return Promise.reject('两次密码输入不一致');
            }
            _password = ''
            if(_data.form.password2 && _password2==='err') validatePassword2()
            return Promise.resolve();
         }},
      ],
      password2: [
        { required: true,validator: (_rule, value) => {
            if (!value) {
              return Promise.reject('请确认密码');
            }
            if(!Verify.password.test(value)) return Promise.reject('密码为6-20位的数字字母组成');
            if(_data.form.password&&value !== _data.form.password) {
              _password2 = 'err'
              return Promise.reject('两次密码输入不一致');
            }
            _password2 = ''
             if(_data.form.password && _password==='err') validatePassword()
            return Promise.resolve();
        }}
      ],
      code: [
        { required: true, message: '请输入验证码' }
      ]
		}
	})
  const validatePassword = () => {
      registerFormRef.value.validateFields('password');
  }
  const validatePassword2 = () => {
    registerFormRef.value.validateFields('password2');
  }
  const openPage = (type) => {
    window.open('/protocolPolicy?type=' + type, '_blank');
  }
	function submit() {
    registerFormRef.value.validate().then(() => {
			// promiseModalRef.value.open(_data.form.code, _data.form);
      forgotPasswordRepass({
        usermail:_data.form.systemUserId,
        password:md5(md5(_data.form.password)),
        checkpassword:md5(md5(_data.form.password2)),
        code:_data.form.code,
      }).then((res) => {
        notification.success({
          message: '提示',
          description: '修改密码成功'
        });
        // userStore.setShareCode('')
        // // backLogin()
        // userStore.setUserinfo(res.data);
        // userStore.setToken(res.data.access_token);
        // userStore.setShowLogin(false)
        backLogin()
      })
		})
	}

	// 发送验证码
function sendCode() {
    registerFormRef.value.validateFields('systemUserId').then(() => {
      _data.disSendCode = true
      if (reg.test(_data.form.systemUserId)) {
        getEmailCode({mail: _data.form.systemUserId}).then(res => {
          notification.success({
            message: '提示',
            description: '发送成功'
          });
          downTime();
        },err=>{
          _data.disSendCode = false
        })
      }
      if (regPhone.test(_data.form.systemUserId)) {
        getCode({phone: _data.form.systemUserId}).then(res => {
          notification.success({
            message: '提示',
            description: '发送成功'
          });
          downTime();
        }, err => {
          _data.disSendCode = false
        })
      }
    })
	}

function downTime() {
		clearInterval(_data.time.t);
		_data.time.n = 60;
		_data.time.t = setInterval(() => {
			_data.time.n--;
			if(_data.time.n<=0) {
				clearInterval(_data.time.t);
			}
      _data.disSendCode = false
		}, 1000);
	}

const emits = defineEmits(['back']);
const backLogin = () => {
  emits('back')
}

</script>

<style lang="less" scoped>
.register-wp {
  width: 100%;
  .form-box {
    width: 100%;
    //border-radius: 4px;
    //box-shadow: 0 0 10px rgba(15,163,127,.6);
    .title {
      padding: 0 0 20px;
      font-size: 28px;
      text-align: center;
      color: #ffffff;
    }
    .t-form {
      width:100%;

      :deep(.ant-form-item) {
        padding-top: 5px;
        margin-bottom: 20px;
      }
      :deep(.ant-form-item-with-help) {
        margin-bottom:0!important;
      }
      :deep(.ant-form-item-label > label) {
        color:#ffffff;
      }

      .ipt {
        border-radius: 8px;
        height: 40px;
        background-color: inherit;
        border-color: #242837;
        color:#ffffff;
        :deep(.ant-input) {
          color: #fff;
          font-size: 16px;
          background-color:inherit;
        }
        :deep(.ant-input-prefix) {
          margin-right: 10px;
        }
        :deep(.ant-input-password-icon,.anticon-eye,.ant-btn-link) {
          color: #fff;
        }
        :deep(.ant-btn-link) {
          color: #999;
        }
        :deep(.ant-btn-link[disabled],.ant-btn-link[disabled]:hover) {
          color: #666
        }
      }
      :deep(.ant-form-item-explain-error){
        font-size:13px;
        line-height: 20px;
      }
      :deep(.ant-form-item-with-help .ant-form-item-explain){
        min-height: 20px;
      }
    }
    .sub-btn {
      color: #9C9C9E;
    }
    .btn {
      flex: 1;
      height: 40px;
      font-size: 16px;
      border-radius: 8px;
      color: #ffffff;
      border: 0;
      background: @btn-bg-color;
      margin: 0 0 15px;
    }
  }
}
</style>
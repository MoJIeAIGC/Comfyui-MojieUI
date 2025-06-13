<template>
  <a-modal v-model:visible="_data.visible" title="忘记密码"
  	okText="确认"
  	cancelText="取消"
  	@ok="handleOk">
    <a-form :label-col="{style: {width: '7em'}}">
    	<a-form-item label="登录用户名" v-bind="oForm1.validateInfos.code">
    		<a-input v-model:value="_d.form.code" placeholder="请输入"/>
    	</a-form-item>
    	<a-form-item label="手机号" v-bind="oForm1.validateInfos.cellphone">
    		<a-input v-model:value="_d.form.cellphone" placeholder="请输入"/>
    	</a-form-item>
    	<a-form-item label="验证码" v-bind="oForm2.validateInfos.yzm">
		   	<div class="send-box">
		   		<a-input class="ipt" v-model:value="_data.form.vcode" placeholder="请输入"></a-input>
		   		<a-button v-if="_data.time.n <= 0" class="btn" type="primary" @click="sendCode()">获取验证码</a-button>
					<a-button v-else class="btn" disabled>{{ _data.time.n }}秒</a-button>
		   	</div>
		  </a-form-item>
			<a-form-item label="新密码" v-bind="oForm2.validateInfos.password">
				<a-input-password v-model:value="_data.form.password" placeholder="请输入"></a-input-password>
			</a-form-item>
			<a-form-item label="确认新密码" v-bind="oForm2.validateInfos.password2">
				<a-input-password v-model:value="_data.form.password2" placeholder="请输入"></a-input-password>
			</a-form-item>
	</a-form>
  </a-modal>
</template>

<script setup>
	import { reactive, ref, onMounted } from 'vue'
	import {Form, notification} from "ant-design-vue";

	import {ApiPost} from "@/api/api.js";
	import {Verify} from "@/utils/Tools.js";

	const _data = reactive({
		visible: false,

		form: {
			code: '',
			cellphone: '',
			vcode: '',
			password: '',
			password2: ''
		},

		time: {
			n: 0,
			t: null
		},

		rules1: {
			code: [
		 		{ required: true, message: '请输入登录用户名' }
		 	],
		 	cellphone: [
		 		{ required: true, message: '请输入手机号' },
		 		{ pattern: Verify.phone, message: '请输入正确的手机号码'}
		 	],
		},

		rules2: {
			vcode: [
		 		{ required: true, message: '请输入验证码' }
		 	],
			password: [
		 		{ required: true, message: '请输入密码' },
				{ pattern: Verify.password, message: '密码为6-20位的数字字母组成'}
		 	],
			password2: [
		 		{ required: true, message: '请确认密码' },
		 		{ validator: (_rule, value) => {
		 			if(value !== _data.form.password) {
		 				return Promise.reject('两次密码输入不一致');
		 			}
					return Promise.resolve();
		 		} },
		 	],
		}
	})

	const oForm1 = Form.useForm(_data.form, _data.rules1);
	const oForm2 = Form.useForm(_data.form, _data.rules2);

	function open() {
		_data.visible = true;
	}

	function handleOk() {
		Promise.all([oForm1.validate(), oForm2.validate()]).then(() => {
			ApiPost("/Web/forgetpassword", _data.form).then(res => {
				notification.success({
					message: '提示',
					description: '修改密码成功，请登录'
				});
				_data.visible = false;
			})
		})
	}


	function sendCode() {
		oForm1.validate().then(() => {
			ApiPost("/Web/getsmscode/"+_data.form.cellphone).then(res => {
				downTime();
				notification.success({
					message: '提示',
					description: '验证码已发送成功',
				});
			})
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
		}, 1000);
	}


	defineExpose({
		open
	})

</script>

<style lang="less" scoped>

.send-box {
	display: flex;
	justify-content: space-between;
	gap: 10px;
	.ipt {
		width: 0;
		flex: 1;
	}
	.btn {
		padding: 0;
		width: 84px;
	}
}
</style>
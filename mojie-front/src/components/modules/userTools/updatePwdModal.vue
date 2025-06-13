<template>
  <a-modal v-model:visible="_data.visible" title="更改密码"
  	okText="确认"
  	cancelText="取消"
  	@ok="handleOk">
    <a-form :label-col="{style: {width: '7em'}}">
			<a-form-item label="原密码" v-bind="validateInfos.passwordOld">
				<a-input-password v-model:value="_data.form.passwordOld" placeholder="请输入"></a-input-password>
	   	</a-form-item>
    	<a-form-item label="新密码" v-bind="validateInfos.passwordNew">
				<a-input-password v-model:value="_data.form.passwordNew" placeholder="请输入"></a-input-password>
	   	</a-form-item>
		  <a-form-item label="确认新密码" v-bind="validateInfos.passwordNew2">
				<a-input-password v-model:value="_data.form.passwordNew2" placeholder="请输入"></a-input-password>
		  </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup>
	import { reactive } from 'vue'
	import {Form, notification} from "ant-design-vue";
  import md5 from 'md5';
	import {updatePws} from "@/api/login.js";
	import {Verify} from "@/utils/Tools.js";

  import {useUserStore} from '@/store/userStore.js';
  import {useOrderStore} from "@/store/orderStore.js";
  const userStore = useUserStore();

	const _data = reactive({
		visible: false,

		form: {
			passwordOld: '',
			passwordNew: '',
			passwordNew2: '',
		},

		rules: {
			passwordOld: [
		 		{ required: true, message: '请输入原密码' },
				{ pattern: Verify.password, message: '密码为6-20位的数字字母组成'}
		 	],
			passwordNew: [
		 		{ required: true, message: '请输入新密码' },
				{ pattern: Verify.password, message: '密码为6-20位的数字字母组成'}
		 	],
			 passwordNew2: [
		 		{ required: true, message: '请确认新密码' },
		 		{ validator: (_rule, value) => {
		 			if(value !== _data.form.passwordNew) {
		 				return Promise.reject('两次新密码输入不一致');
		 			}
					return Promise.resolve();
		 		}},
		 	],
		},
	})

	const {validate, validateInfos} = Form.useForm(_data.form, _data.rules);

	function open() {
		_data.visible = true;
	}

	function handleOk() {
		validate().then(() => {
			let params = {
        oldpassword: md5(md5(_data.form.passwordOld)),
        password: md5(md5(_data.form.passwordNew)),
        checkpassword: md5(md5(_data.form.passwordNew2)),
			}
      updatePws(params).then((res) => {
         console.log(res.code === 200)
        if(res.code === 200) {
          notification.success({
            message: '提示',
            description: '修改成功，请重新登录'
          });
          useOrderStore().setOrderInfo({})
          userStore.logout();
        }
      })
		})
	}

	defineExpose({
		open
	})

</script>

<style lang="less" scoped>
.userName {
	color: #333;
}
</style>
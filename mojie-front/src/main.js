import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import store from "./store/index.js";
import VueLazyload from 'vue-lazyload';
// 引入antd
import Antd from "ant-design-vue";
import "@/assets/css/theme-antd.less";
import "@/assets/iconfont/iconfont.css";
import directives from './directive'
import waterfall from 'vue-waterfall2'
import loading from '@/assets/image/loading.png';
import loading1 from '@/assets/image/loading3.gif';
import {useUserStore} from './store/userStore';
setTimeout(() => {
	let arr = ['gpt-4o-image','flex','qiHua']
	if(!arr.includes(useUserStore().modelType)){
		useUserStore().setModelType('qiHua');
	}
}, 200);
createApp(App)
.use(router)
.use(store)
.use(directives)
.use(VueLazyload, {
	preLoad: 1.3,
	error: loading,
	loading: loading1,
	attempt:2
})
.use(Antd)
.use(waterfall)
.mount('#app')

/**
 * 全站http配置
 *
 * axios参数说明
 */
import axios from 'axios';
import {serialize} from '@/utils/utils';
import { message } from 'ant-design-vue';
//默认请求地址
 axios.defaults.baseURL = import.meta.env.VITE_APP_BASE_URL
//默认超时时间
axios.defaults.timeout = 5 * 60 * 1000;
//返回其他状态码
axios.defaults.validateStatus = function (status) {
    return status >= 200 && status <= 500;
};
import {useUserStore} from '@/store/userStore';
import {useOrderStore} from "@/store/orderStore.js";
//跨域请求，允许保存cookie
axios.defaults.withCredentials = true;
// NProgress 配置
// NProgress.configure({
//     showSpinner: false
// });
const userStore = useUserStore()
//http request拦截
axios.interceptors.request.use( (config) => {
    //开启 progress bar
  //  NProgress.start();
  //  const meta = (config.meta || {});
    //让每个请求携带token
    // const token = getStore({name:"token"});
    if (!config.noToken&&userStore.token) {
        config.headers['Authorization'] = `Bearer ${userStore.token}`;
        // config.headers['token'] =user.token
    }
    //headers中配置text请求
    if (config.text === true) {
        config.headers["Content-Type"] = "text/plain";
    }
    if (userStore.token&&(config.method === 'GET'||config.method === 'get')) {
        config.params = config.params || {}; // 确保 params 存在
        config.params.userid = userStore.userinfo.userId;
    }
    //headers中配置serialize为true开启序列化
    if (config.method === 'POST') {
        config.data = serialize(config.data);
    }
    return config
}, error => {
    return Promise.reject(error)
});
//http response 拦截
axios.interceptors.response.use(res => {
    //关闭 progress bar
   //  NProgress.done();
    //获取状态码
    let status = res.data.code || res.status;
    if(status===401|| status==='token_not_valid' ||res.status===401) {
        userStore.logout();
        useOrderStore().setOrderInfo({})
        userStore.setShowLogin(true);
    }
    if(status !== 200 && res.data.status){
        if(res.data.status === 'success') status = 200
    }
   // const statusWhiteList = website.statusWhiteList || [];
    const msg = res.data.msg || res.data.message||'未知错误';
    if (status !== 200&&status!==401&& res.status!==401) {
        message.error(msg).then(r => {});
        return Promise.reject(res)
    }
    return res.data;
}, error => {
    return Promise.reject(error);
});

export default axios;

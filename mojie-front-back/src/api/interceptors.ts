import axios from 'axios';
import { useTokenStore } from '@/store/tokenStore';

// 创建一个 Axios 实例
const api = axios.create();

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const tokenStore = useTokenStore();
    const token = tokenStore.access_token;
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;
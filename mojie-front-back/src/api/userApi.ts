import api from './interceptors';
import { useTokenStore } from '@/store/tokenStore';
import { BASE_API_URL } from '../config/apiConfig';

// 设置 axios 的默认配置，让其携带跨域凭证
api.defaults.withCredentials = true;

export const login = async (formData: FormData) => {
  try {
    const response = await api.post(`${BASE_API_URL}/api/user/mojie/login`, formData);
    console.log('服务器返回的完整响应:', response); 
    return response.data;
  } catch (error) {
    console.error('用户登录失败', error);
    throw error;
  }
};



export const addproxy = async (formData: FormData) => {
  try {
    const response = await api.post(`${BASE_API_URL}/api/user/proxy/create-proxy/`, formData);
    console.log('服务器返回的完整响应:', response); 
    return response.data;
  } catch (error) {
    console.error('用户登录失败', error);
    throw error;
  }
};




export const logout = async () => {
  const tokenStore = useTokenStore();
  const { refresh_token } = tokenStore;
  const formData = new FormData();
  formData.append('refresh_token', refresh_token);
  try {
    const response = await api.post(`${BASE_API_URL}/api/user/mojie/logout`, formData);
    return response.data;
  } catch (error) {
    console.error('用户登出失败', error);
    throw error;
  }
};

// 返回用户数据
export const getUser = async () => {
  try {
    const response = await api.get(`${BASE_API_URL}/api/user/mojie/list`);
    return response.data;
  } catch (error) {
    console.error('获取数据失败', error);
    throw error;
  }
};


// 返回用户数据
export const getassets = async () => {
  try {
    const response = await api.get(`${BASE_API_URL}/api/user/assets`);
    return response.data;
  } catch (error) {
    console.error('获取数据失败', error);
    throw error;
  }
};


// 修改用户信息
export const updatesssets = async (productData: any) => {
  const pk = productData.id; // 从商品数据中获取主键
  const url = `${BASE_API_URL}/api/user/assets/${pk}/`;
  try {
    const response = await api.put(url, productData);
    return response;
  } catch (error) {
    console.error('更新商品数据失败', error);
    throw error;
  }
};



// 修改用户信息
export const updateUser = async (productData: any) => {
  const pk = productData.id; // 从商品数据中获取主键
  const url = `${BASE_API_URL}/api/user/mojie/user_update/${pk}/`;
  try {
    const response = await api.put(url, productData);
    return response;
  } catch (error) {
    console.error('更新商品数据失败', error);
    throw error;
  }
};


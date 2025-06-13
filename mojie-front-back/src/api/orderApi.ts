// import axios from 'axios';
import api from './interceptors';
import { BASE_API_URL } from '../config/apiConfig';


// 返回订单数据
export const getOrder = async (page: number, pageSize: number) => {
  try {
    const response = await api.get(`${BASE_API_URL}/api/pay/mojie/order_list?page=${page}&page_size=${pageSize}`);
    return response.data;
  } catch (error) {
    console.error('获取数据失败', error);
    throw error;
  }
};

// 返回套餐数据
export const getproduct = async () => {
    try {
      const response = await api.get(`${BASE_API_URL}/api/pay/mojie/product_list`);
      return response.data;
    } catch (error) {
      console.error('获取数据失败', error);
      throw error;
    }
  };

// 修改商品
export const updateProduct = async (productData: any) => {
  const pk = productData.id; // 从商品数据中获取主键
  const url = `${BASE_API_URL}/api/pay/mojie/product/${pk}/`;
  try {
    const response = await api.put(url, productData);
    return response;
  } catch (error) {
    console.error('更新商品数据失败', error);
    throw error;
  }
};


// 返回营业额数据
export const getmoney = async () => {
  try {
    const response = await api.get(`${BASE_API_URL}/api/pay/mojie/money_list`);
    return response.data;
  } catch (error) {
    console.error('获取数据失败', error);
    throw error;
  }
};
// 返回营业额数据
export const uc = async () => {
  try {
    const response = await api.get(`${BASE_API_URL}/api/pay/usercount`);
    return response.data;
  } catch (error) {
    console.error('获取数据失败', error);
    throw error;
  }
};


  // 删除套餐
  export const delpro = async (tagid: number = 0) => {
    try {
      // 使用传入的 tagid 构建请求 URL
      const response = await api.delete(`${BASE_API_URL}/api/pay/product/${tagid}/`);
      return response.data;
    } catch (error) {
      console.error('获取数据失败', error);
      throw error;
    }
  };
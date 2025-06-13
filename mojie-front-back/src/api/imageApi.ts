// import axios from 'axios';
import api from './interceptors';
import { BASE_API_URL } from '../config/apiConfig';

export const uploadImage = async (formData: FormData) => {
  try {
    const response = await api.post(`${BASE_API_URL}/api/image/img_upload`, formData);
    return response.data;
  } catch (error) {
    console.error('上传图片时出错:', error);
    throw error;
  }
};

// 返回图片数据
export const getAllImage = async (page: number, pageSize: number) => {
  try {
    const response = await api.get(`${BASE_API_URL}/api/image/get_all_images?page=${page}&page_size=${pageSize}`);
    return response.data;
  } catch (error) {
    console.error('获取数据失败', error);
    throw error;
  }
};

// 新增模板
export const addTemp = async (formData: FormData) => {
  try {
    const response = await api.post(`${BASE_API_URL}/api/temp/usertotemp/`, formData);
    return response.data;
  } catch (error) {
    console.error('上传图片时出错:', error);
    throw error;
  }
};
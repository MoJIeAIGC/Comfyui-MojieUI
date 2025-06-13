// import axios from 'axios';
import api from './interceptors';
import { BASE_API_URL } from '../config/apiConfig';


// 返回图片数据
export const getqueue = async (page: number, pageSize: number) => {
    try {
      const response = await api.get(`${BASE_API_URL}/api/image/queue/admin/?completed_page=${page}&page_size=${pageSize}`);
      return response.data;
    } catch (error) {
      console.error('获取数据失败', error);
      throw error;
    }
  };


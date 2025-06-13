// import axios from 'axios';
import api from './interceptors';
import { BASE_API_URL } from '../config/apiConfig';


// 新增案例
export const addExam = async (formData: FormData) => {
  try {
    const response = await api.post(`${BASE_API_URL}/api/temp/addExam/`, formData);
    return response.data;
  } catch (error) {
    console.error('上传图片时出错:', error);
    throw error;
  }
};

// 返回案例数据
// 新增 tagid 参数，默认为 1
export const getexamples = async (tagid: number = 0, cateid: number = 0,page: number, pageSize: number) => {
    try {
      // 使用传入的 tagid 构建请求 URL
      const response = await api.get(`${BASE_API_URL}/api/temp/examples?tagid=${cateid}&cateid=${tagid}&page=${page}&page_size=${pageSize}`);
      return response.data.data;
    } catch (error) {
      console.error('获取数据失败', error);
      throw error;
    }
  };

// 新增模板
export const addTemp = async (formData: FormData) => {
    try {
      const response = await api.post(`${BASE_API_URL}/api/temp/addTemp/`, formData);
      return response.data;
    } catch (error) {
      console.error('上传图片时出错:', error);
      throw error;
    }
  };



// 返回模板数据
// 新增 tagid 参数，默认为 1
export const gettemplates = async ( cateid: number = 0,tagid: number = 0,page: number, pageSize: number) => {
    try {
      // 使用传入的 tagid 构建请求 URL
      const response = await api.get(`${BASE_API_URL}/api/temp/templates?tagid=${tagid}&cateid=${cateid}&page=${page}&page_size=${pageSize}`);
      return response.data.data;
    } catch (error) {
      console.error('获取数据失败', error);
      throw error;
    }
  };


// 返回标签数据
export const gettag = async (temp: number = 0) => {
    try {
      const response = await api.get(`${BASE_API_URL}/api/temp/category?temp=${temp}`);
      return response.data;
    } catch (error) {
      console.error('获取数据失败', error);
      throw error;
    }
  };
// 返回标签数据
export const getrealtag = async (temp: number = 0) => {
    try {
      const response = await api.get(`${BASE_API_URL}/api/temp/tag?temp=${temp}`);
      return response.data;
    } catch (error) {
      console.error('获取数据失败', error);
      throw error;
    }
  };
  
  export const getsmall = async (cate_id: number = 0) => {
    try {
      const response = await api.get(`${BASE_API_URL}/api/temp/getsmall?cate_id=${cate_id}`);
      return response.data;
    } catch (error) {
      console.error('获取数据失败', error);
      throw error;
    }
  };

// 修改标签
export const edittag = async (productData: any) => {
  const pk = productData.id; // 从商品数据中获取主键
  const url = `${BASE_API_URL}/api/temp/tag/${pk}/update/`;
  try {
    const response = await api.put(url, productData);
    return response;
  } catch (error) {
    console.error('更新商品数据失败', error);
    throw error;
  }
};
// 添加标签
export const addTag = async (formData: FormData) => {
  try {
    const response = await api.post(`${BASE_API_URL}/api/temp/addtag/`, formData);
    return response.data;
  } catch (error) {
    console.error('上传图片时出错:', error);
    throw error;
  }
};

// 修改标签
export const editrealtag = async (productData: any) => {
  const pk = productData.id; // 从商品数据中获取主键
  const url = `${BASE_API_URL}/api/temp/realtag/${pk}/update/`;
  try {
    const response = await api.put(url, productData);
    return response;
  } catch (error) {
    console.error('更新商品数据失败', error);
    throw error;
  }
};
// 添加标签
export const addrealTag = async (formData: FormData) => {
  try {
    const response = await api.post(`${BASE_API_URL}/api/temp/addrealtag/`, formData);
    return response.data;
  } catch (error) {
    console.error('上传图片时出错:', error);
    throw error;
  }
};




  // 删除案例
  export const delexam = async (tagid: number = 0) => {
    try {
      // 使用传入的 tagid 构建请求 URL
      const response = await api.delete(`${BASE_API_URL}/api/temp/example/${tagid}/`);
      return response.data;
    } catch (error) {
      console.error('获取数据失败', error);
      throw error;
    }
  };

  export const deltemp = async (tagid: number = 0) => {
    try {
      // 使用传入的 tagid 构建请求 URL
      const response = await api.delete(`${BASE_API_URL}/api/temp/template/${tagid}/`);
      return response.data;
    } catch (error) {
      console.error('获取数据失败', error);
      throw error;
    }
  };

  export const delrealtag = async (tagid: number = 0) => {
    try {
      // 使用传入的 tagid 构建请求 URL
      const response = await api.delete(`${BASE_API_URL}/api/temp/delrealtag/${tagid}/`);
      return response.data;
    } catch (error) {
      console.error('获取数据失败', error);
      throw error;
    }
  };
  export const deltag = async (tagid: number = 0) => {
    try {
      // 使用传入的 tagid 构建请求 URL
      const response = await api.delete(`${BASE_API_URL}/api/temp/deltag/${tagid}/`);
      return response.data;
    } catch (error) {
      console.error('获取数据失败', error);
      throw error;
    }
  };

    // 编辑案例
    export const editExam = async (productData: any) => {
      try {
        // 使用传入的 tagid 构建请求 URL
        const pk = productData.get("id") // 从商品数据中获取主键
        console.log(pk)
        const response = await api.patch(`${BASE_API_URL}/api/temp/example/${pk}/update/`,productData);
        return response.data;
      } catch (error) {
        console.error('获取数据失败', error);
        throw error;
      }
    };

    // 编辑案例
    export const editTemp = async (productData: any) => {
      try {
        // 使用传入的 tagid 构建请求 URL
        const pk = productData.get("id") // 从商品数据中获取主键
        console.log(pk)
        const response = await api.patch(`${BASE_API_URL}/api/temp/template/${pk}/update/`,productData);
        return response.data;
      } catch (error) {
        console.error('获取数据失败', error);
        throw error;
      }
    };

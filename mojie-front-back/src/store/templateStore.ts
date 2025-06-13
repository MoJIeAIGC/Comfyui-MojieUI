import { defineStore } from 'pinia';
import { gettemplates, gettag } from '@/api/templateApi';

export const useTemplateStore = defineStore('template', {
  state: () => ({
    allData: [],
    tagList: [],
    total: 0,
  }),
  actions: {
    async fetchTags() {
      try {
        const response = await gettag();
        if (Array.isArray(response.data)) {
          this.tagList = response.data;
        } else {
          console.error('获取标签数据失败，响应不是数组:', response);
        }
      } catch (error) {
        console.error('获取标签数据失败:', error);
      }
    },
    async fetchData(tagId = null) {
      try {
        const response = await gettemplates(tagId);
        console.log('API 响应:', response);
        if (Array.isArray(response.data)) {
          this.allData = response.data;
          this.total = response.data.length;
        } else {
          console.error('API 响应不是数组:', response);
          this.allData = [];
          this.total = 0;
        }
      } catch (error) {
        console.error('获取示例数据失败:', error);
      }
    },
  },
});
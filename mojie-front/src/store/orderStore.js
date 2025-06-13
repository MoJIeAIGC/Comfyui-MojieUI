import { defineStore } from 'pinia';
export const useOrderStore = defineStore('order',{
    state: () => {
      return {
          orderInfo:{}
      }
  },
  getters: {},
  actions: {
    // 更新状态
    setOrderInfo(data) {
        this.orderInfo = data
    }
  },
  persist: false
})
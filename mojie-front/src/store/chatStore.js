import { defineStore } from 'pinia';
export const useChatStore = defineStore('chat',{
    state: () => {
      return {
          resolutionType:'1:1',
          generatorType:'1',
          draInfo:{}
      }
  },
  getters: {},
  actions: {
    // 更新状态
    setDraInfo(data) {
        this.draInfo = data
    },
     setResolutionType(data) {
        this.resolutionType = data
    },
      setGeneratorType(data) {
        this.generatorType = data
    }
  },
  persist: true
})
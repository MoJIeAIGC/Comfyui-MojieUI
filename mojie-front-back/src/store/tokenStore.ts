import { defineStore } from 'pinia'

export const useTokenStore = defineStore('token', {
  state: () => ({
    access_token: '',
    refresh_token: ''
  }),
  actions: {
    setTokens(accessToken: string, refreshToken: string) {
      this.access_token = accessToken
      this.refresh_token = refreshToken
    },
    clearTokens() {
      this.access_token = ''
      this.refresh_token = ''
    }
  },
  persist: {
    enabled: true, //Store中数据持久化生效
  },
})
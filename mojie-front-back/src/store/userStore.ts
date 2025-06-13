import { defineStore } from 'pinia';

export const useUserStore = defineStore('user', {
  state: () => ({
    // 添加用户名和用户 ID 状态
    username: null as string | null,
    userId: null as number | null,
  }),
  actions: {
    // 添加设置用户名的方法
    setUsername(username: string) {
      this.username = username;
    },
    // 添加设置用户 ID 的方法
    setUserId(userId: number) {
      this.userId = userId;
    },
  },
  // persist: true, // 启用持久化，确保刷新页面后数据仍存在
  persist: {
    enabled: true, // Store 中数据持久化生效
  },
});
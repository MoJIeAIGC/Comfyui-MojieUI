
import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';

const store = createPinia();
//数据持久化
store.use(piniaPluginPersistedstate);

export default store;

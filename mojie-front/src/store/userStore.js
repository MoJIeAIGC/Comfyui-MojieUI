import {defineStore} from 'pinia';

export const useUserStore = defineStore('user', {

    state: () => {
        return {
            showLogin: false,
            token: '',
            userinfo: null,
            modelType: 'qiHua',
            points: 0,
            dataTime: '',
            shareCode:'',
            vipInfo:'',
            myShareCode:'',
        }
    },
    getters: {
        getToken(state) {
            return state.token;
        },
        getShareCode(state) {
            return state.shareCode;
        },
        getShowLogin(state) {
            return state.showLogin;
        },
        getUserinfo(state) {
            return state.userinfo;
        },
        getModelType(state) {
            return state.modelType;
        }
    },
    actions: {
        // 更新状态
        setToken(data) {
            this.dataTime = new Date().getTime();
            this.token = data;
        },
        setUserinfo(data) {
            this.userinfo = data;
        },
        setShowLogin(data) {
            this.showLogin = data;
        },
        // 更新模型类型
        setModelType(data) {
            this.modelType = data;
        },   // 更新模型类型
        setPoints(data) {
            this.points = data;
        },
        setShareCode(data) {
            this.shareCode = data;
        },
        setVipInfo(data) {
            this.vipInfo = data;
        },

        // 退出登录
        logout() {
            this.token = '';
            this.dataTime = '';
            this.userinfo = '';
            this.points = '';
           // this.showLogin = true;
           //router.replace({path: '/login'})
        }
    },
    //持久化储存
    persist: true
})
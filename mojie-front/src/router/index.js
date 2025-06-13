import { createRouter, createWebHistory } from 'vue-router'
import {useUserStore} from "@/store/userStore.js";
import {useOrderStore} from "@/store/orderStore.js";


const routes = [
  {
    path: '/',
    meta:{
      title:'登录'
    },
    redirect: '/home'
  },
  {
    path: '/index',
    name: 'index',
    meta:{
      title:'首页'
    },
    component: () => import ("@/views/index/index.vue"),
    children:[
      {
        path: '/home',
        name: 'home',
        meta:{
          title:'首页'
        },
        component: () => import ("@/views/home/index.vue")
      },
      {
        path: '/gallery',
        name: 'gallery',
        meta:{
          title:'画廊'
        },
        component: () => import ("@/views/home/gallery.vue")
      },
      {
        path: '/chat',
        name: 'chat',
        meta:{
          title:'会话'
        },
        component: () => import ("@/views/chat/index.vue")
      },
      {
        path: '/about',
        name: 'about',
        meta:{
          title:'关于我们'
        },
        component: () => import ("@/views/about/index.vue")
      },
      {
        path: '/recharge',
        name: 'recharge',
        meta:{
          title:'会员算力充值'
        },
        component: () => import ("@/views/pay/recharge.vue")
      },
      {
        path: '/acting',
        name: 'acting',
        meta:{
          title:'图片代做'
        },
        component: () => import ("@/views/acting/index.vue")
      },
      // {
      //   path: '/video',
      //   name: 'video',
      //   meta:{
      //     title:'视频'
      //   },
      //   component: () => import ("@/views/video/index.vue")
      // },
    ]
  },
  {
    path: '/test',
    name: 'test',
    meta:{
      title:'调试画板'
    },
    component: () => import ("@/views/test/index.vue")
  },
  {
    path: '/payStatus',
    name: 'payStatus',
    meta:{
      title:'支付宝支付回调'
    },
    component: () => import ("@/views/pay/payCallback.vue")
  },
  {
    path: '/protocolPolicy',
    name: 'protocolPolicy',
    meta:{
      title:'协议政策'
    },
    component: () => import ("@/views/user/protocolPolicy.vue")
  },
  // {
  //   path: '/login',
  //   name: 'login',
  //   meta:{
  //     title:'登录'
  //   },
  //   component: () => import ("@/views/user/login.vue")
  // },
  { path: '/:catchAll(.*)',   component: () => import ("@/components/error-page/404.vue") }
]

const Router = createRouter({
  history: createWebHistory(import.meta.env.VITE_PUBLIC_PATH),
  routes: routes
})

Router.beforeEach((to, from) => {
  const userStore = useUserStore();
  let isExpire = 1
  if(userStore.dataTime)  isExpire =  new Date().getTime() - userStore.dataTime - 23 * 60 * 60 * 1000 - 55*60*1000;
  if(to.path === '/test'|| to.path === '/payStatus') return true
  // if(to.path === '/home') return true
  if(['/login','/protocolPolicy'].indexOf(to.path) === -1) { //非登录页不存在token或token超时
    if(!userStore.token || isExpire > 0) {
      userStore.logout()
      useOrderStore().setOrderInfo({})
    }
  }
  // else {
  //   if(userStore.dataTime&&userStore.token) {
  //     if(isExpire < 0 )  return { path: '/home', query: to.query }
  //   }
  // }
  if (to.query.shareCode) {
    const newQuery = { ...to.query };
     userStore.setShareCode(newQuery.shareCode)
     delete newQuery.shareCode;
     return { path: to.path, query: newQuery }
  }
  return true;
})

export default Router
import {createRouter, createWebHistory, createWebHashHistory} from 'vue-router'
import { useTokenStore } from '@/store/tokenStore';
const router = createRouter({
    // history: createWebHistory(   .meta.env.BASE_URL),
    history: createWebHashHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            name: 'home',
            component: () => import("@/views/HomeView.vue"),
            meta: {
                title: '首页',
            }
        },{
            path: '/login',
            name: 'login',
            meta: {
                title: '登录',
                noLayout:true,
                requiresAuth: true // 添加这一行
            },
            component: () => import("@/views/LoginView.vue")
        }, {
            path: '/exam/list',
            name: 'exam',
            component: () => import("@/views/examView.vue")
        }, {
            path: '/temp/list',
            name: 'temp',
            component: () => import("@/views/temp.vue")
        },{
            path: '/text/list',
            name: 'text',
            component: () => import("@/views/text.vue")
        },
        {
            path: '/image/list',
            name: 'image',
            component: () => import("@/views/ImageList.vue")
        }, 
        {
            path: '/order/list',
            name: 'order',
            component: () => import("@/views/OrderList.vue")
        }, 
        {
            path: '/product/list',
            name: 'product',
            component: () => import("@/views/ProductList.vue")
        }, 
        {
            path: '/image/add',
            name: 'addimage',
            component: () => import("@/views/ImageAddView.vue")
        }, 
        {
            path: '/:pathMatch(.*)*',
            name: 'notFound',
            component: () => import("@/views/NotFoundView.vue")
        },
        {
            path: '/about',
            name: 'about',
            component: () => import("@/views/AboutView.vue")
        }, {
            path: '/list/:id',
            name: 'list',
            meta: {
                title: '列表',
            },
            component: () => import("@/views/ListView.vue")
        }, {
            path: '/log/list',
            name: 'log',
            meta: {
                title: '列表',
            },
            component: () => import("@/views/ExternalView.vue")
        },{
            path: '/queue',
            name: 'queue',
            component: () => import("@/views/queueList.vue")
        },{
            path: '/examcat',
            name: 'examcat',
            component: () => import("@/views/sbexam.vue")
        }
    ]
})

router.beforeEach((to, from, next) => {
    const tokenStore = useTokenStore();
    console.log("tokenStore",tokenStore.access_token)
    console.log("to",to.meta.requiresAuth)
    if (!to.meta.requiresAuth && !tokenStore.access_token) {
      // 如果需要认证且用户未登录，重定向到登录页面
      next('/login');
    } else {
      next();
    }
  });

export default router

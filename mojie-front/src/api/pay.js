import request from './axios';

const url = import.meta.env.VITE_APP_BASE_URL;
// 获取加速包接口
export const getProductList = (params) => {
    return request({
        url: `${url}/api/pay/mojie/product_list/`,
        withCredentials: false,
        method: 'get',
        params
    })
}
//产品列表
export const getProList = (params) => {
    return request({
        url: `${url}/api/pay/getpro/`,
        withCredentials: false,
        method: 'get',
        params
    })
}
//生成订单
export const getPayWechat = (data) => {
    return request({
        url: `${url}/api/pay/wechat_pay_pc/`,
        withCredentials: false,
        method: 'post',
        data
    })
}
//查询订单
export const getOrderDetails = (params) => {
    return request({
        url: `${url}/api/pay/getorder_pc/`,
        withCredentials: false,
        method: 'get',
        params
    })
}
// 支付
export const payProduct = (data) => {
    return request({
        url: `${url}/api/pay/product/payment/`,
        withCredentials: false,
        method: 'post',
        data
    })
}
// // 查看支付算力
// export const getUserSeek = (params) => {
//     return request({
//         url: `${url}/api/user/mojie/user_seek`,
//         withCredentials: false,
//         method: 'get',
//         params
//     })
// }
// 查看支付算力
export const getUserSeek = (params) => {
    return request({
        url: `${url}/api/user/userinfo`,
        withCredentials: false,
        method: 'get',
        params
    })
}
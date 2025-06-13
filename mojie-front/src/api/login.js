import request from './axios';
// const url_32 =  'http://192.168.1.32:8000'
const url =  ''
// 手机登陆or注册
export const loginByPhone = (data) => {
    return request({
        url: `${url}/api/user/phlogin`,
        withCredentials: false,
        method: 'post',
        noToken: true,
        data
    })
}
//手机验证码
export const getCode = (data) => {
    return request({
        url: `${url}/api/user/phoncode`,
        withCredentials: false,
        noToken: true,
        method: 'post',
        data
    })
}
//图形证码
export const getCaptcha = (params) => {
    return request({
        url: `${url}/api/image/getCaptcha`,
        withCredentials: false,
        noToken: true,
        method: 'get',
        params
    })
}
// 邮箱登陆or注册
export const loginByEmail = (data) => {
    return request({
        url: `${url}/api/user/maillogin`,
        withCredentials: false,
        noToken: true,
        method: 'post',
        data
    })
}
//邮箱验证码
export const getEmailCode = (data) => {
    return request({
        url: `${url}/api/user/mailcode`,
        withCredentials: false,
        noToken: true,
        method: 'post',
        data
    })
}
//密码登录
export const loginByUser = (data) => {
    return request({
        url: `${url}/api/user/login`,
        withCredentials: false,
        noToken: true,
        method: 'post',
        data
    })
}
//注册
export const registerUser = (data) => {
    return request({
        url: `${url}/api/user/register`,
        withCredentials: false,
        noToken: true,
        method: 'post',
        data
    })
}
//忘记密码
export const forgotPasswordRepass = (data) => {
    return request({
        url: `${url}/api/user/repass`,
        withCredentials: false,
        noToken: true,
        method: 'post',
        data
    })
}
//修改密码
export const updatePws = (data) => {
    return request({
        url: `${url}/api/user/cgpass`,
        withCredentials: false,
        method: 'put',
        data
    })
}
//退出登录
export const loginOut = (data) => {
    return request({
        url: `${url}/api/user/logout`,
        withCredentials: false,
        method: 'post',
        data
    })
}

export const queryUserShareCode = () => {
    return request({
        url: '/api/user/get_share_code',
        method: 'GET'
    })
}
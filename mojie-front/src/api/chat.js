import request from './axios';

// const url_32 =  'http://192.168.1.32:8000'
//const url = import.meta.env.VITE_APP_BASE_URL;

// const url = 'http://192.168.1.16:9152'
// const url = 'http://192.168.1.34'
const url = import.meta.env.VITE_APP_BASE_URL;
// gpt生图
// export const postChatGPT = (data) => {
//     return request({
//         url: `${url}/api/image/image_ChatGPT_API_product`,
//         withCredentials: false,
//         method: 'post',
//         data
//     })
// }
// gpt生图   http://127.0.0.1:9152/api/image/image_ChatGPT_NEW_API_product
export const postChatGPT = (data) => {
    return request({
     //   url: `${url}/api/image/image_ChatGPT_NEW_API_product`,
        url: `${url}/api/image/image_ChatGPT_OPENAI_API_product`,
        withCredentials: false,
        method: 'post',
        data
    })
}
export const postChatRetry = (task_id) => {
    return request({
        url: `${url}/api/image/tasks/${task_id}/retry`,
        withCredentials: false,
        method: 'post'
    })
}
// google gemini改图
export const postGemini = (data) => {
    return request({
        url: `${url}/api/image/image_Gemini_API_product`,
        withCredentials: false,
        method: 'post',
        data
    })
}
// Flex-综合绘图
export const postCombined = (data) => {
    return request({
        url: `${url}/api/image/combined_image_generation`,
        withCredentials: false,
        method: 'post',
        data
    })
}
// Flex-综合绘图
// http://192.168.1.16:9500/api/image/flux-kontext-pro/image/generation/
export const postFluxKonTextCombined = (data,type) => {
    return request({
      //    flux-kontext-pro/image/flux/generation/
        url: type === 'flex' ? `${url}/api/image/flux-kontext-pro/image/flux/generation/` : `${url}/api/image/flux-kontext-pro/image/generation/`,
        withCredentials: false,
        method: 'post',
        data
    })
}
// 奇画30
export const postVolcengine = (data) => {
    return request({
        url: `${url}/api/image/image_Volcengine_SDK_API_product`,
        withCredentials: false,
        method: 'post',
        data
    })
}
// 根据用户和会话查询消息
// http://192.168.1.32:8000/api/image/get_user_images?userid=1&sessionid=1
export const getUserImages = (params) => {
    return request({
        url: `${url}/api/image/get_user_images`,
        withCredentials: false,
        method: 'get',
        params
    } )
}
// 会话列表
export const getNewConver = (userid) => {
    return request({
        url: `${url}/api/image/getConver`,
        withCredentials: false,
        method: 'get',
        params:{
            userid
        }
    })
}
// 会话列表
export const getUserRequests = (conversation_id,user_id) => {
    return request({
        url: `${url}/api/user-requests/`,
        withCredentials: false,
        method: 'get',
        params:{
            user_id,
            conversation_id
        }
    })
}

// 新建会话
export const newConver = (data) => {
    return request({
        url: `${url}/api/image/newConver`,
        withCredentials: false,
        method: 'post',
        data
    })
}
// 删除会话
export const delNewConver = (data) => {
    return request({
        url: `${url}/api/image/delConver`,
        withCredentials: false,
        method: 'delete',
        data
    })
}
// 删除消息
export const delChat = (record_id) => {
    return request({
        url: `${url}/api/image/del_rec`,
        withCredentials: false,
        method: 'POST',
        data:{
            record_id
        }
    })
}
// 队列
export const imageQueue = (params) => {
    return request({
        url: `${url}/api/image/queue/info/`,
        withCredentials: false,
        method: 'get',
        params
    })
}
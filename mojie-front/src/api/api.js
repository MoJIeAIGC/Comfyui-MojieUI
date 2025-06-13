import request from './axios';
// const url_32 =  'http://192.168.1.32:8000'
const url_16 =  ''
// const url_16 =  'http://192.168.1.16:8000'

export const ApiGet = () => {
    return request({
      //  url: `/api/apps/qcd/productDict/list`,
        url: `${url_16}/api/video/num_man`,
        withCredentials: false,
        method: 'post',
        data: {
            num:2,
            user_id:1
        }
    })
}
export const ApiPost = () => {
    return request({
      //  url: `/api/apps/qcd/productDict/list`,
        url: `${url_16}/api/video/num_man`,
        withCredentials: false,
        method: 'post',
        data: {
            num:2,
            user_id:1
        }
    })
}
export const ApiDownGet = () => {
    return request({
      //  url: `/api/apps/qcd/productDict/list`,
        url: `${url_16}/api/video/num_man`,
        withCredentials: false,
        method: 'post',
        data: {
            num:2,
            user_id:1
        }
    })
}

export const loginByPhone = (data) => {
    return request({
        url: `${url_16}/api/video/num_man`,
        withCredentials: false,
        method: 'post',
        data
    })
}
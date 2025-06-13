import request from './axios';
// const url = import.meta.env.VITE_APP_BASE_URL;
const url =  ''

export const uploadImg = (data) => {
    return request({
        url: `${url}/api/image/img_upload`,
        withCredentials: false,
        method: 'post',
        data
    })
}
export const delUploadImg = (id) => {
    if(!id) return
    return request({
        url: `${url}/api/image/images/delete/`,
        withCredentials: false,
        method: 'delete',
        data:{
            image_id: id,
        }
    })
}
//上传视频、音频
export const postUploadVideo = (data) => {
    return request({
        url: `${url}/api/video/upload/`,
        withCredentials: false,
        method: 'post',
        data
    })
}
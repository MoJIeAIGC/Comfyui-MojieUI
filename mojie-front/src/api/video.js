import request from './axios';

export const postVideoGeneration = (video,audio) => {
    return request({
        url: `/api/video/runninghub/`,
        withCredentials: false,
        method: 'post',
        data:{
            video,
            audio
        }
    })
}
export const getVideoStatus = (id) => {
    return request({
        url: `/api/video/status/${id}/`,
        withCredentials: false,
        method: 'get'
    })
}

// 视频列表
export const getVideos = () => {
    return request({
        url: `/api/video/getvideos`,
        withCredentials: false,
        method: 'get'
    })
}
// 视频列表
export const delVideos = (id) => {
    return request({
        url: `/api/video/delvideos/`,
        withCredentials: false,
        method: 'post',
        data:{
            id
        }
    })
}
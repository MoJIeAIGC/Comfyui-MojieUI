import request from "./axios.js";

// const baseUrl = import.meta.env.VITE_APP_BASE_URL;

export const queryCategory = () => {
    return request({
        url: `/api/temp/category`,
        method: 'get'
    })
}

export const queryTag = () => {
    return request({
        url: `/api/temp/tag`,
        method: 'get',
        params:{
            temp:1
        }
    })
}

export const queryTemplates = (params) => {
    return request({
        url: `/api/temp/tempweb` ,
        method: 'get',
        params
    })
}

export const queryTempGood = (params) => {
    return request({
        url: `/api/temp/good`,
        method: 'get',
        params
    })
}
import request from "./axios.js";

// const baseUrl = import.meta.env.VITE_APP_BASE_URL;

export const queryCategory = () => {
    return request({
        url: `/api/temp/category`,
        method: 'get',
        params:{
            temp:0
        }
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

export const queryExamples = (params) => {
    return request({
        url: `/api/temp/examples`,
        method: 'get',
        params
    })
}
export const queryTempGood = (params) => {
    return request({
        url: `/api/temp/goodexam`,
        method: 'get',
        params
    })
}
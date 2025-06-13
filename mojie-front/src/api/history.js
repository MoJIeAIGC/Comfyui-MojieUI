import request from "./axios.js";

export const getHistoryList = (page, size) => {
    return request({
        url: '/api/image/points-deduction-history/',
        method: 'GET',
        data: {
            page: page,
            page_size: size
        }
    })
}
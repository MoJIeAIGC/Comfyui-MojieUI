import request from "./axios.js";
import {uploadImg} from "@/api/upload.js";

// const baseUrl = import.meta.env.VITE_APP_BASE_URL;
//生成白底图
export const getWhiteImage = (imageUrl) => {
    return request({
        url: '/api/image/white_image_product',
        method: 'post',
        data: {
            url: imageUrl,
            product_id: 1
        }
    })
}
export const getWhiteImageFile = (data) => {
    return request({
        url: '/api/image/white_image_product_only',
        method: 'post',
        data
    })
}
//定时查询白底图结果
export const queryGenerateImage = (queryUrl) => {
    return request({
        url: queryUrl,
        method: 'get'
    })
}

//迁移替换
export const replaceProductImage = (data) => {
    return request({
        url: '/api/image/image_workflow_product',
        method: 'POST',
        data
    })
}
//细节精修，局部重绘
export const useImageDetailRefinement = (data) => {
    return request({
        url: '/api/image/image_fine_detail_product',
        method: 'POST',
        data
    })
}
//扩图
export const useImageExpend = (data) => {
    return request({
        url: '/api/image/image_wide_picture',
        method: 'POST',
        data
    })
}

export const imageInternal = (data) => {
    return request({
        url: '/api/image/image_internal_supplement',
        method: 'POST',
        data
    })
}
export const imageInternalRemoval = (data) => {
    return request({
        url: '/api/image/image_internal_supplement_removal',
        method: 'POST',
        data
    })
}
export const colorAdjustment = (data) => {
    return request({
        url: '/api/image/color_adjustment',
        method: 'POST',
        data
    })
}
export const getTranslateToEn = (text) => {
    return request({
        url: '/api/image/translate',
        method: 'post',
        data:{
            text
        }
    })
}
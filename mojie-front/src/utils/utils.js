import Compressor from "compressorjs";
import {modelList} from "@/options/model.js";

export function findArrItem (id,key,arr) {
    return arr.filter(item=>item[key] === id)
}
export const hasRouterItem = (id,arr) => {
    let flag = false
    for(const item of arr) {
        if (item.path === id || (item.children && item.children.length&&hasRouterItem(id,item.children))) {
            flag = true
            break
        }
    }
    return flag
}
export const serialize = (data) => {
    const list = [];
    Object.keys(data).forEach(ele => {
        list.push(`${ele}=${data[ele]}`)
    })
    return list.join('&');
};
export const getUid = (length = 8) => {
    if (length > 0) {
        const data = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"];
        let nums = "";
        for (let i = 0; i < length; i++) {
            const r = parseInt(String(Math.random() * 61));
            nums += data[r];
        }
        return nums + new Date().getTime();
    } else {
        return false;
    }
}
export const isHttp = (url) => {
    return url.indexOf('http://') !== -1 || url.indexOf('https://') !== -1
}

export const isImageFile  = (type) => {
    const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'];
    return imageTypes.includes(type);
}
export const isVideoFile  = (type) => {
    const imageTypes = ['video/', 'video/mp4', 'video/avi', 'video/mov', 'video/ogg'];
    return imageTypes.includes(type);
}
export const convertImgToBase64 = (url, callback,_data) =>{
    var canvas = document.createElement('canvas')
    var ctx = canvas.getContext('2d')
    var img = new Image()
    img.crossOrigin = 'Anonymous'
    if(_data){
      //  img.style = `filter: brightness(${_data.brightness}%) contrast(${_data.contrast}%) saturate(${_data.saturate}%`
    }
    img.onload = function() {
        canvas.height = img.height
        canvas.width = img.width
      //  canvas.style = `filter: brightness(${_data.brightness}%) contrast(${_data.contrast}%) saturate(${_data.saturate}%`
        ctx.drawImage(img, 0, 0)
        // var dataURL = canvas.toDataURL('image/png');
       // adjustImage(canvas, _data.brightness/100, _data.contrast/100, _data.saturate/100);
        var dataURL = canvas.toDataURL('image/jpeg')
        callback.call(this, dataURL)
        canvas = null
    }
    img.src = url
}
export const convertImgToBase64Src = (url, callback,_data) =>{
    var canvas = document.createElement('canvas')
    var ctx = canvas.getContext('2d')
    var img = new Image()
    img.crossOrigin = 'Anonymous'
    img.onload = function() {
        canvas.height = img.height
        canvas.width = img.width
        ctx.drawImage(img, 0, 0)
        adjustImage(canvas, _data.brightness, _data.contrast/100, _data.saturate/100);
        var dataURL = canvas.toDataURL('image/jpeg')
        callback.call(this, dataURL)
        canvas = null
    }
    img.src = url
}

export const adjustImage = (canvas, brightness, contrast, saturation) => {
    let ctx = canvas.getContext('2d');
    let imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    let data = imgData.data;

    // 调整亮度、对比度和饱和度
    for (let i = 0; i < data.length; i += 4) {
        let r = data[i];
        let g = data[i + 1];
        let b = data[i + 2];
        let a = data[i + 3];

        // 调整亮度 (brightness)
        r += brightness;
        g += brightness;
        b += brightness;
        // 确保RGB值在0到255之间
        r = r < 0 ? 0 : r > 255 ? 255 : r;
        g = g < 0 ? 0 : g > 255 ? 255 : g;
        b = b < 0 ? 0 : b > 255 ? 255 : b;

        // 调整对比度 (contrast)
        r = (r - 128) * contrast + 128;
        g = (g - 128) * contrast + 128;
        b = (b - 128) * contrast + 128;
        r = r < 0 ? 0 : r > 255 ? 255 : r;
        g = g < 0 ? 0 : g > 255 ? 255 : g;
        b = b < 0 ? 0 : b > 255 ? 255 : b;

        // 调整饱和度 (saturation) - 这里使用简单的线性变换，实际应用中可能需要更复杂的算法如HSV模型
        let avg = (r + g + b) / 3;
        r = avg + (r - avg) * saturation;
        g = avg + (g - avg) * saturation;
        b = avg + (b - avg) * saturation;
        r = r < 0 ? 0 : r > 255 ? 255 : r;
        g = g < 0 ? 0 : g > 255 ? 255 : g;
        b = b < 0 ? 0 : b > 255 ? 255 : b;

        data[i] = r;
        data[i + 1] = g;
        data[i + 2] = b;
    }

    // 将修改后的数据放回Canvas
    ctx.putImageData(imgData, 0, 0);
}
// canvas转化成base64
export const canvasTobase64 = (canvas)=> {
    const width = canvas.width
    const height = canvas.height
    const URL = canvas.toDataURL({
        format: 'jpeg',
        quality: 1,
        multiplier: 1,
        left: 0,
        top: 0,
        width: width,
        height: height
    })
    return URL
}

export const base64UrlToFile = (base64Url) => {
    if(!base64Url) return
    // 获取到base64编码
    const arr = base64Url.split(',');
    const mime = arr[0].match(/:(.*?);/)[1];
    // 将base64编码转为字符串
    const bstr = atob(arr[1]);
    let n = bstr.length;
    // 创建初始化为0的，包含length个元素的无符号整型数组
    const u8arr = new Uint8Array(n);
    while (n--) {
        u8arr[n] = bstr.charCodeAt(n);
    }
    const type = mime.split('/')[1];
    return new File([u8arr], 'edt-image'+ new Date().getTime() + '.'+type, { type: mime });
};
//压缩图片至3m以内
export const compressFile = (file, callBack,type) => {
    const reader = new FileReader();
    reader.onload = function (event) {
        const img = new Image();
        img.onload = function () {
            const MAX_SIZE = 3 * 1024 * 1024; // 3MB in bytes
            // let width = img.width;
            // let height = img.height;
            //
            // const ratio = Math.min(MAX_SIZE / file.size, 1);
            // width *= Math.sqrt(ratio);
            // height *= Math.sqrt(ratio);
            // width = width * ratio;
            // height = height * ratio;

            // minWidth?: number;
            // minHeight?: number;
            let maxObj = {}
            if(type=== 'extend') maxObj = {   maxWidth: 1280,maxHeight: 1280 }
            new Compressor(file, {
                quality: 0.9, // 压缩质量，范围0到1，0.6表示60%的质量
                ...maxObj,
                convertSize: MAX_SIZE,
                success: (blob) => {
                    const _file = new File([blob], blob.name, {type: blob.type});
                    console.log(_file.size/1024/1024);
                    callBack(_file); // 上传压缩后的文件
                },
                error: (err) => {
                    console.error('Something went wrong!', err.message);
                },
            });
        };
        img.src = event.target.result;
    };
    reader.readAsDataURL(file);
};
export const getModelByKey = (key) => {
    let index = 1
    if(key&&(key.indexOf('gpt')!==-1||key.indexOf('GPT')!==-1)){
        index =  0
    }
    if(key&&(key.indexOf('gemini')!==-1)){
        index =  -1
    }
    // if(key&&(key.indexOf('flex')!==-1 || key.indexOf('ai_')!==-1)){
    //   return 'Flex-综合绘图'
    // }
    if(key&&(key.indexOf('volcengine')!==-1||key.indexOf('dou')!==-1)){
        index = 2
    }
    return modelList[index]|| {}
}
//获取最大公约数
export const gcd = (a, b) => {
    while (b !== 0) {
        let temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}
export const handleDownloadQrIMg = (imgUrl,name='download') => {
    // 这里是获取到的图片base64编码
    // 如果浏览器支持msSaveOrOpenBlob方法（也就是使用IE浏览器的时候），那么调用该方法去下载图片
    if (window.navigator.msSaveOrOpenBlob) {
        let bstr = atob(imgUrl.split(',')[1])
        let n = bstr.length
        let u8arr = new Uint8Array(n)
        while (n--) {
            u8arr[n] = bstr.charCodeAt(n)
        }
        let blob = new Blob([u8arr])
        window.navigator.msSaveOrOpenBlob(blob, name + '.png')
    } else {
        // 这里就按照chrome等新版浏览器来处理
        let a = document.createElement('a')
        a.href = imgUrl
        a.setAttribute('download', name +'.png')
        a.click()
    }
}
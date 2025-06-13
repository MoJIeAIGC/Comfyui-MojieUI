

import viewerImg from './viewerImg' // 复制
import drawImg from './drawImg' // 复制

const directives = {
    'db-click-img':viewerImg,
    'draw-start':drawImg,
}

export default {
    install(Vue) {
        Object.keys(directives).forEach((key) => {
            Vue.directive(key, directives[key])
        })
    }
}
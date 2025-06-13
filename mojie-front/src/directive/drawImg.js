// import { h } from 'vue'
// import { ElMessageBox } from 'element-plus'
import 'viewerjs/dist/viewer.css'
import viewer from 'viewerjs'
export default {
    mounted(el, binding) {
        el.addEventListener('dragstart', (e) => {
            let src =  e.target.src
            if(src.includes("?x-tos-process=image/resize")) src  = src.split('?x-tos-process=image/resize')[0]
            event.dataTransfer.setData('text/plain', src); // 设置拖动数据，通常是图片的URL
        });
    },
    updated(el, binding) {

    },
    unmounted(el, binding) {
        el.removeEventListener('dragstart', () => {});
    }
}
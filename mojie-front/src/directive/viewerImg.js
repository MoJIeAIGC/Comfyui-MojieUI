// import { h } from 'vue'
// import { ElMessageBox } from 'element-plus'
import 'viewerjs/dist/viewer.css'
import viewer from 'viewerjs'
export default {
    mounted(el, binding) {
        el.addEventListener('dblclick', () => {
            if(el.src){
                let flag = false
                if(el.src.includes("?x-tos-process=image/resize")) flag = true

                var img = new Image()
                img.crossOrigin = 'Anonymous'
                if(flag)  img.src = el.src.split('?x-tos-process=image/resize')[0]
                // ElMessageBox({
                //     customClass:'viewer-img',
                //     title: '图片预览',
                //     message:  h('img', { src: el.src }, 'VNode'),
                // }).then((e) => {
                //      console.log(e)
                //     }) .catch((action) => {
                //        console.log(action)
                //     })
                const gallery = new viewer(flag?img:el, {
                    navbar:false,
                    toolbar: false,
                    movable: true,
                    hide(){
                        gallery.destroy()
                    }
                })
                gallery.show()
            }
        });
    },
    updated(el, binding) {

    },
    unmounted(el, binding) {
        el.removeEventListener('dblclick', () => {});
    }
}
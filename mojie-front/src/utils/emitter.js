import mitt from 'mitt'

//调用mitt，得到emitter,emitter可以绑定事件和触发事件
const emitter = mitt()

//暴露emitter
export default emitter